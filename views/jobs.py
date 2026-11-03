import json
import streamlit as st
import db
import pipeline
import re
import documents
import pipeline

st.title("Jobs")

profile = db.get_profile()
has_resume = len(profile["resume_text"].strip()) >= 100
if not has_resume:
    st.info("Save your resume in the Profile page first.")


def start_job():
    """Button callback: runs before the page reruns, so it can clear the input boxes."""
    url = st.session_state["new_url"].strip()
    desc = st.session_state["new_desc"].strip()
    if not url and not desc:
        st.session_state["form_error"] = "Give a URL or paste a description."
        return
    st.session_state["pending_run"] = db.create_job(url, desc)
    st.session_state["new_url"] = ""
    st.session_state["new_desc"] = ""


def queue(job_id, step=None):
    if step:
        pipeline.reset_step(job_id, step)
    st.session_state["pending_run"] = job_id


def set_status(job_id):
    db.update_status(job_id, st.session_state[f"status_{job_id}"])

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@st.cache_data
def make_file(kind, fmt, text):
    return documents.build(kind, fmt, text)


def file_stem(job):
    name = job["company"] or job["title"] or f"job{job['id']}"
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or f"job{job['id']}"


def download_row(job, kind, text, raw_ext):
    stem = f"{kind}_{file_stem(job)}"
    key = f"{kind}_{job['id']}"
    c1, c2, c3 = st.columns(3)
    c1.download_button("Word (.docx)", make_file(kind, "docx", text),
                       file_name=f"{stem}.docx", mime=DOCX_MIME, key=f"{key}_docx")
    c2.download_button("PDF", make_file(kind, "pdf", text),
                       file_name=f"{stem}.pdf", mime="application/pdf", key=f"{key}_pdf")
    c3.download_button(f"Text (.{raw_ext})", text,
                       file_name=f"{stem}.{raw_ext}", key=f"{key}_raw")


def run_with_progress(job_id):
    with st.status("Running pipeline...", expanded=True) as status:
        try:
            ok = pipeline.run_pipeline(job_id, on_progress=st.write)
        except pipeline.PipelineError as e:
            status.update(label=str(e), state="error")
            return
        if ok:
            status.update(label="Done", state="complete")
        else:
            status.update(label="Stopped. Open the job below to retry.", state="error")


st.text_input("Job URL", key="new_url")
st.text_area("...or paste the job description (used instead of the URL if filled)",
             height=150, key="new_desc")
st.button("Process job", type="primary", on_click=start_job, disabled=not has_resume)

error = st.session_state.pop("form_error", None)
if error:
    st.error(error)

pending_run = st.session_state.pop("pending_run", None)
if pending_run:
    run_with_progress(pending_run)

st.divider()
st.subheader("Your jobs")
jobs = db.list_jobs()
if not jobs:
    st.caption("Nothing here yet.")

for j in jobs:
    name = " at ".join(x for x in (j["title"], j["company"]) if x) or j["url"] or "Untitled job"
    score = "-" if j["score"] is None else j["score"]
    flag = " (failed)" if j["error"] else ""
    with st.expander(f"{name} | {score} | {j['status']}{flag}"):
        if j["url"]:
            st.caption(j["url"])
        if j["error"]:
            st.error(j["error"])

        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1], vertical_alignment="bottom")
        c1.selectbox("Status", db.STATUSES, index=db.STATUSES.index(j["status"]),
                     key=f"status_{j['id']}", on_change=set_status, args=(j["id"],))
        if pipeline.pending_steps(j):
            c2.button("Retry" if j["error"] else "Continue", key=f"go_{j['id']}",
                      on_click=queue, args=(j["id"],))
        if j["resume_md"]:
            c3.button("Redo resume", key=f"rt_{j['id']}", on_click=queue, args=(j["id"], "tailor"))
        if j["cover_letter"]:
            c4.button("Redo letter", key=f"rc_{j['id']}", on_click=queue, args=(j["id"], "cover"))
        c5.button("Delete", key=f"del_{j['id']}", on_click=db.delete_job, args=(j["id"],))

        fit_tab, resume_tab, cover_tab, log_tab = st.tabs(["Fit", "Resume", "Cover letter", "Log"])

        with fit_tab:
            if j["fit_json"]:
                fit = json.loads(j["fit_json"])
                st.metric("Fit score", fit["score"])
                st.write(fit["summary"])
                left, right = st.columns(2)
                with left:
                    st.markdown("**Strengths**")
                    for s in fit["strengths"]:
                        st.write(f"- {s}")
                with right:
                    st.markdown("**Gaps**")
                    for g in fit["gaps"]:
                        st.write(f"- {g}")
                if fit["red_flags"]:
                    st.warning("Red flags: " + "; ".join(fit["red_flags"]))
            else:
                st.caption("Not run yet.")

        with resume_tab:
            if j["resume_md"]:
                review = json.loads(j["review_json"]) if j["review_json"] else None
                if review is None or not review["checked"]:
                    st.caption("Not fact-checked.")
                elif review["issues"]:
                    st.warning("The reviewer still flags these claims. Check them against your "
                               "resume before using this: " + "; ".join(review["issues"]))
                else:
                    st.caption(f"Fact-check: no unsupported claims found (round {review['rounds']}).")
                st.markdown(j["resume_md"])
                if j["resume_notes"]:
                    st.markdown("**What changed**")
                    st.markdown(j["resume_notes"])
                    download_row(j, "resume", j["resume_md"], "md")
            else:
                st.caption("Not run yet.")

        with cover_tab:
            if j["cover_letter"]:
                st.code(j["cover_letter"], language=None, wrap_lines=True)
                download_row(j, "letter", j["cover_letter"], "txt")
            else:
                st.caption("Not run yet.")

        with log_tab:
            for e in db.list_events(j["id"]):
                st.caption(f"{e['created_at']} | {e['step']} | {e['status']} {e['message']}")