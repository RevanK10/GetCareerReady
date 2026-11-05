import json

import pytest

import pipeline
from scraper import ScrapeError

FIT = {"title": "Eng", "company": "Acme", "score": 77, "summary": "s",
       "strengths": [], "gaps": [], "red_flags": []}


@pytest.fixture
def steps(tmp_db, monkeypatch):
    """Fake every model/network call, count the calls, and let tests inject failures."""
    monkeypatch.setattr(pipeline, "RETRY_DELAY", 0)
    s = type("S", (), {})()
    s.calls = {"fetch": 0, "fit": 0, "tailor": 0, "review": 0, "cover": 0}
    s.tailor_failures = []      # exceptions to raise, one per tailor call
    s.review_results = []       # lists of issues, or exceptions, one per review call
    s.feedback_seen = []
    s.scrape_error = None

    def scrape(url):
        s.calls["fetch"] += 1
        if s.scrape_error:
            raise s.scrape_error
        return "Fetched description " * 20

    def analyze(resume, job):
        s.calls["fit"] += 1
        return dict(FIT)

    def tailor(resume, job, feedback=None):
        s.calls["tailor"] += 1
        s.feedback_seen.append(feedback)
        if s.tailor_failures:
            raise s.tailor_failures.pop(0)
        return {"resume": f"v{s.calls['tailor']}", "notes": "n"}

    def review(original, tailored):
        s.calls["review"] += 1
        result = s.review_results.pop(0) if s.review_results else []
        if isinstance(result, Exception):
            raise result
        return {"issues": result}

    def cover(resume, job, name="", title="", company=""):
        s.calls["cover"] += 1
        return f"Dear team, {name}"

    monkeypatch.setattr(pipeline, "scrape_job", scrape)
    monkeypatch.setattr(pipeline, "analyze_fit", analyze)
    monkeypatch.setattr(pipeline, "tailor_resume", tailor)
    monkeypatch.setattr(pipeline, "review_resume", review)
    monkeypatch.setattr(pipeline, "write_cover_letter", cover)
    s.db = tmp_db
    return s


def test_pasted_description_skips_fetch(steps):
    job_id = steps.db.create_job("", "Pasted description")
    assert pipeline.run_pipeline(job_id) is True
    job = steps.db.get_job(job_id)
    assert steps.calls["fetch"] == 0
    assert (job["title"], job["company"], job["score"]) == ("Eng", "Acme", 77)
    assert job["cover_letter"] == "Dear team, Jane Doe" and pipeline.pending_steps(job) == []


def test_url_job_fetches_description(steps):
    job_id = steps.db.create_job("http://a.com/job", "")
    assert pipeline.run_pipeline(job_id) is True
    assert len(steps.db.get_job(job_id)["description"]) > 200


def test_existing_title_is_not_overwritten(steps):
    job_id = steps.db.create_job("", "d")
    steps.db.update_job(job_id, title="My title")
    pipeline.run_pipeline(job_id)
    assert steps.db.get_job(job_id)["title"] == "My title"


def test_failure_keeps_earlier_work_and_retry_resumes(steps):
    job_id = steps.db.create_job("", "d")
    steps.tailor_failures = [RuntimeError("down")] * 2          # both attempts fail
    assert pipeline.run_pipeline(job_id) is False
    job = steps.db.get_job(job_id)
    assert job["score"] == 77 and job["error"].startswith("tailor:")
    assert pipeline.pending_steps(job) == ["tailor", "cover"]

    steps.calls["fit"] = 0
    assert pipeline.run_pipeline(job_id) is True
    assert steps.calls["fit"] == 0 and steps.db.get_job(job_id)["error"] == ""


def test_transient_failure_is_retried(steps):
    job_id = steps.db.create_job("", "d")
    steps.tailor_failures = [RuntimeError("blip")]
    assert pipeline.run_pipeline(job_id) is True
    assert [e["status"] for e in steps.db.list_events(job_id) if e["step"] == "tailor"] == [
        "start", "retry", "start", "done"]


def test_scrape_error_is_not_retried(steps):
    steps.scrape_error = ScrapeError("blocked")
    job_id = steps.db.create_job("http://b.com", "")
    assert pipeline.run_pipeline(job_id) is False
    assert steps.calls["fetch"] == 1 and "blocked" in steps.db.get_job(job_id)["error"]


def test_redo_one_step_only(steps):
    job_id = steps.db.create_job("", "d")
    pipeline.run_pipeline(job_id)
    steps.calls.update(fit=0, tailor=0, cover=0)
    pipeline.reset_step(job_id, "cover")
    assert pipeline.pending_steps(steps.db.get_job(job_id)) == ["cover"]
    pipeline.run_pipeline(job_id)
    assert steps.calls["cover"] == 1 and steps.calls["fit"] == 0 and steps.calls["tailor"] == 0


def test_reset_clears_review_and_rejects_fetch(steps):
    job_id = steps.db.create_job("", "d")
    pipeline.run_pipeline(job_id)
    pipeline.reset_step(job_id, "tailor")
    job = steps.db.get_job(job_id)
    assert job["resume_md"] == "" and job["review_json"] == ""
    with pytest.raises(ValueError):
        pipeline.reset_step(job_id, "fetch")


def test_pipeline_guards(steps):
    job_id = steps.db.create_job("", "d")
    with pytest.raises(pipeline.PipelineError, match="not found"):
        pipeline.run_pipeline(999)
    empty = steps.db.create_job("", "")
    with pytest.raises(pipeline.PipelineError, match="no description"):
        pipeline.run_pipeline(empty)
    steps.db.save_profile({"resume_text": ""})
    with pytest.raises(pipeline.PipelineError, match="resume"):
        pipeline.run_pipeline(job_id)


def test_cover_step_receives_title_and_company(steps, monkeypatch):
    seen = {}

    def cover(resume, job, name="", title="", company=""):
        seen.update(name=name, title=title, company=company)
        return "letter"

    monkeypatch.setattr(pipeline, "write_cover_letter", cover)
    job_id = steps.db.create_job("", "d")
    pipeline.run_pipeline(job_id)
    assert seen == {"name": "Jane Doe", "title": "Eng", "company": "Acme"}


# reviewer loop

def review_of(steps, job_id):
    return json.loads(steps.db.get_job(job_id)["review_json"])


def test_review_passes_first_time(steps):
    job_id = steps.db.create_job("", "d")
    pipeline.run_pipeline(job_id)
    assert steps.calls["tailor"] == 1
    assert review_of(steps, job_id) == {"checked": True, "issues": [], "rounds": 1}


def test_review_issue_triggers_rewrite_with_feedback(steps):
    steps.review_results = [["fake PhD"], []]
    job_id = steps.db.create_job("", "d")
    pipeline.run_pipeline(job_id)
    assert steps.feedback_seen == [None, ["fake PhD"]]
    assert steps.db.get_job(job_id)["resume_md"] == "v2"
    assert review_of(steps, job_id)["rounds"] == 2


def test_review_gives_up_after_max_revisions_but_keeps_resume(steps):
    steps.review_results = [["a"], ["b"], ["c"]]
    job_id = steps.db.create_job("", "d")
    assert pipeline.run_pipeline(job_id) is True
    assert steps.calls["tailor"] == pipeline.MAX_REVISIONS + 1
    result = review_of(steps, job_id)
    assert result["issues"] == ["c"] and result["checked"] is True
    assert steps.db.get_job(job_id)["error"] == ""


def test_reviewer_failure_keeps_resume_without_rewriting(steps):
    steps.review_results = [RuntimeError("reviewer down")]
    job_id = steps.db.create_job("", "d")
    assert pipeline.run_pipeline(job_id) is True
    assert steps.calls["tailor"] == 1
    assert review_of(steps, job_id)["checked"] is False