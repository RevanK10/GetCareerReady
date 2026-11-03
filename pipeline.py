import json
import time

import db
from cover import write_cover_letter
from fit import analyze_fit
from scraper import ScrapeError, scrape_job
from tailor import tailor_resume

MAX_ATTEMPTS = 2
RETRY_DELAY = 2


class PipelineError(RuntimeError):
    """The pipeline can't start (no resume, unknown job)."""


def step_fetch(job, profile):
    return {"description": scrape_job(job["url"])}


def step_fit(job, profile):
    fit = analyze_fit(profile["resume_text"], job["description"])
    updates = {"fit_json": json.dumps(fit), "score": fit["score"]}
    if not job["title"]:
        updates["title"] = fit["title"]
    if not job["company"]:
        updates["company"] = fit["company"]
    return updates


def step_tailor(job, profile):
    out = tailor_resume(profile["resume_text"], job["description"])
    return {"resume_md": out["resume"], "resume_notes": out["notes"]}


def step_cover(job, profile):
    letter = write_cover_letter(profile["resume_text"], job["description"], profile["full_name"])
    return {"cover_letter": letter}


STEPS = [
    ("fetch", "description", step_fetch),
    ("fit", "fit_json", step_fit),
    ("tailor", "resume_md", step_tailor),
    ("cover", "cover_letter", step_cover),
]

# What to blank out so a step runs again.
CLEARS = {
    "fit": {"fit_json": "", "score": None},
    "tailor": {"resume_md": "", "resume_notes": ""},
    "cover": {"cover_letter": ""},
}


def _is_done(job, column):
    return bool((job.get(column) or "").strip())


def pending_steps(job):
    return [name for name, column, _ in STEPS if not _is_done(job, column)]


def reset_step(job_id, step):
    if step not in CLEARS:
        raise ValueError(f"Can't redo step: {step}")
    db.update_job(job_id, error="", **CLEARS[step])


def _fail(job_id, step, error, say):
    db.update_job(job_id, error=f"{step}: {error}")
    db.add_event(job_id, step, "failed", str(error))
    say(f"{step} failed: {error}")
    return False


def _run_step(job_id, name, func, job, profile, say):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        say(f"Running {name} (attempt {attempt})...")
        db.add_event(job_id, name, "start", f"attempt {attempt}")
        try:
            updates = func(job, profile)
        except ScrapeError as e:
            return _fail(job_id, name, e, say)
        except RuntimeError as e:
            if attempt < MAX_ATTEMPTS:
                db.add_event(job_id, name, "retry", str(e))
                time.sleep(RETRY_DELAY)
                continue
            return _fail(job_id, name, e, say)
        db.update_job(job_id, **updates)
        db.add_event(job_id, name, "done")
        say(f"{name} done.")
        return True


def run_pipeline(job_id, on_progress=None):
    """Run every step that isn't done yet. Returns True if the job is complete."""
    def say(message):
        if on_progress:
            on_progress(message)

    job = db.get_job(job_id)
    if job is None:
        raise PipelineError("Job not found.")
    profile = db.get_profile()
    if len(profile["resume_text"].strip()) < 100:
        raise PipelineError("Save your resume in the Profile page first.")
    if not job["description"].strip() and not job["url"].strip():
        raise PipelineError("This job has no description or URL.")

    db.update_job(job_id, error="")
    for name, column, func in STEPS:
        if _is_done(job, column):
            continue
        if not _run_step(job_id, name, func, job, profile, say):
            return False
        job = db.get_job(job_id)
    say("All steps complete.")
    return True