import streamlit as st

import db

st.set_page_config(page_title="CareerReady", layout="wide")
db.init_db()

pages = [
    st.Page("views/jobs.py", title="Jobs", default=True),
    st.Page("views/profile.py", title="Profile"),
]
st.navigation(pages).run()