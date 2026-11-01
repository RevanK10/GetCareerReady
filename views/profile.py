import streamlit as st

import db
from resume import extract_text

st.title("Profile")
profile = db.get_profile()

uploaded = st.file_uploader("Upload your resume (PDF)", type="pdf")
if uploaded:
    text = extract_text(uploaded)
    if text.strip():
        st.session_state["profile_resume"] = text
    else:
        st.warning("No readable text found. This may be a scanned PDF. Paste the text below instead.")

with st.form("profile_form"):
    full_name = st.text_input("Full name", profile["full_name"])
    col1, col2 = st.columns(2)
    email = col1.text_input("Email", profile["email"])
    phone = col2.text_input("Phone", profile["phone"])
    location = st.text_input("Location", profile["location"])
    links = st.text_input("Links (LinkedIn, GitHub, site)", profile["links"])
    resume_text = st.text_area(
        "Resume text",
        st.session_state.get("profile_resume", profile["resume_text"]),
        height=300,
    )
    saved = st.form_submit_button("Save profile", type="primary")

if saved:
    db.save_profile({
        "full_name": full_name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "location": location.strip(),
        "links": links.strip(),
        "resume_text": resume_text.strip(),
    })
    st.session_state.pop("profile_resume", None)
    st.success("Profile saved.")