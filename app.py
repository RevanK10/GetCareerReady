import streamlit as st
from resume import extract_text
from fit import analyze_fit

st.title("CareerReady")

uploaded = st.file_uploader("Upload your resume (PDF)", type="pdf")
if uploaded:
    st.session_state["resume_text"] = extract_text(uploaded)

resume_text = st.session_state.get("resume_text", "")
if uploaded and not resume_text.strip():
    st.warning("No readable text found. This may be a scanned PDF.")

job = st.text_area("Paste the job description", height=200)

if st.button("Analyze fit"):
    if len(resume_text.strip()) < 100:
        st.error("Upload a text-based resume first.")
    elif not job.strip():
        st.error("Paste a job description.")
    else:
        try:
            with st.spinner("Analyzing..."):
                st.session_state["fit"] = analyze_fit(resume_text, job)
        except RuntimeError as e:
            st.error(str(e))

fit = st.session_state.get("fit")
if fit:
    st.subheader(f"{fit['title']} at {fit['company']}".strip(" at"))
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