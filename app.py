import streamlit as st
from resume import extract_text

st.title("CareerReady")

uploaded = st.file_uploader("Upload your resume (PDF)", type="pdf")

if uploaded:
    resume_text = extract_text(uploaded)
    if resume_text.strip():
        st.text_area("Extracted text", resume_text, height=300)
    else:
        st.warning("No readable text found. This may be a scanned PDF.")