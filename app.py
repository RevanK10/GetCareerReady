import streamlit as st
from resume import extract_text
from fit import analyze_fit
from tailor import tailor_resume

st.title("CareerReady")


def inputs_ok(resume_text, job):
    if len(resume_text.strip()) < 100:
        st.error("Upload a text-based resume first.")
        return False
    if not job.strip():
        st.error("Paste a job description.")
        return False
    return True


uploaded = st.file_uploader("Upload your resume (PDF)", type="pdf")
if uploaded:
    st.session_state["resume_text"] = extract_text(uploaded)

resume_text = st.session_state.get("resume_text", "")
if uploaded and not resume_text.strip():
    st.warning("No readable text found. This may be a scanned PDF.")

job = st.text_area("Paste the job description", height=200)

col1, col2 = st.columns(2)
analyze_clicked = col1.button("Analyze fit")
tailor_clicked = col2.button("Tailor resume")

if analyze_clicked and inputs_ok(resume_text, job):
    try:
        with st.spinner("Analyzing..."):
            st.session_state["fit"] = analyze_fit(resume_text, job)
    except RuntimeError as e:
        st.error(str(e))

if tailor_clicked and inputs_ok(resume_text, job):
    try:
        with st.spinner("Tailoring your resume..."):
            st.session_state["tailored"] = tailor_resume(resume_text, job)
    except RuntimeError as e:
        st.error(str(e))

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