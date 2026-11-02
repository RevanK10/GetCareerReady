import streamlit as st

import db
from fit import analyze_fit
from tailor import tailor_resume
from cover import write_cover_letter
from scraper import scrape_job

st.title("Jobs")

profile = db.get_profile()
resume_text = profile["resume_text"]
if len(resume_text.strip()) < 100:
    st.info("Save your resume in the Profile page first.")


def inputs_ok(resume_text, job):
    if len(resume_text.strip()) < 100:
        st.error("Save your resume in the Profile page first.")
        return False
    if not job.strip():
        st.error("Paste a job description.")
        return False
    return True


def run(label, key, func, *args):
    """Run one LLM task with a spinner and keep the result across reruns."""
    try:
        with st.spinner(label):
            st.session_state[key] = func(*args)
    except RuntimeError as e:
        st.error(str(e))


url = st.text_input("Job URL (optional)")
if st.button("Fetch from URL"):
    if not url.strip():
        st.error("Paste a URL first.")
    else:
        try:
            with st.spinner("Fetching the page..."):
                st.session_state["job_text"] = scrape_job(url.strip())
        except RuntimeError as e:
            st.error(str(e))

job = st.text_area("Job description", height=200, key="job_text")

col1, col2, col3 = st.columns(3)
analyze_clicked = col1.button("Analyze fit")
tailor_clicked = col2.button("Tailor resume")
cover_clicked = col3.button("Write cover letter")

if analyze_clicked and inputs_ok(resume_text, job):
    run("Analyzing...", "fit", analyze_fit, resume_text, job)

if tailor_clicked and inputs_ok(resume_text, job):
    run("Tailoring your resume...", "tailored", tailor_resume, resume_text, job)

if cover_clicked and inputs_ok(resume_text, job):
    run("Writing your cover letter...", "cover_result", write_cover_letter,
        resume_text, job, profile["full_name"])
    if "cover_result" in st.session_state:
        st.session_state["cover_box"] = st.session_state.pop("cover_result")

fit = st.session_state.get("fit")
if fit:
    heading = " at ".join(x for x in (fit["title"], fit["company"]) if x)
    if heading:
        st.subheader(heading)
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
    if st.button("Save this job"):
        db.save_job(fit["title"], fit["company"], job, fit["score"])
        st.success("Saved.")

tailored = st.session_state.get("tailored")
if tailored:
    st.divider()
    orig, new = st.columns(2)
    with orig:
        st.subheader("Original")
        st.text(resume_text)
    with new:
        st.subheader("Tailored")
        st.markdown(tailored["resume"])
    if tailored["notes"]:
        with st.expander("What changed"):
            st.markdown(tailored["notes"])

if "cover_box" in st.session_state:
    st.divider()
    st.subheader("Cover letter")
    st.text_area("Edit before you use it", key="cover_box", height=320)
    st.download_button("Download .txt", data=st.session_state["cover_box"],
                       file_name="cover_letter.txt")

st.divider()
st.subheader("Saved jobs")
jobs = db.list_jobs()
if not jobs:
    st.caption("Nothing saved yet.")
for j in jobs:
    c1, c2, c3, c4 = st.columns([4, 1, 2, 1], vertical_alignment="center")
    c1.write(" at ".join(x for x in (j["title"], j["company"]) if x) or "Untitled job")
    c2.write(j["score"])
    status = c3.selectbox("Status", db.STATUSES, index=db.STATUSES.index(j["status"]),
                          key=f"status_{j['id']}", label_visibility="collapsed")
    if status != j["status"]:
        db.update_status(j["id"], status)
        st.rerun()
    if c4.button("Delete", key=f"del_{j['id']}"):
        db.delete_job(j["id"])
        st.rerun()