import streamlit as st

import db
import interviewer

st.title("Mock interview")

resume_text = db.get_profile()["resume_text"]
if len(resume_text.strip()) < 100:
    st.info("Save your resume in the Profile page first.")
    st.stop()

jobs = [j for j in db.list_jobs() if j["description"].strip()]
if not jobs:
    st.info("Add a job on the Jobs page first.")
    st.stop()


def label(job):
    return " at ".join(x for x in (job["title"], job["company"]) if x) or f"Job {job['id']}"


def start():
    job = db.get_job(st.session_state["iv_job"])
    kind = st.session_state["iv_kind"]
    st.session_state["interview"] = {
        "job_id": job["id"],
        "label": label(job),
        "kind": kind,
        "total": st.session_state["iv_total"],
        "system": interviewer.build_system(job, resume_text, kind),
        "history": [],
        "feedback": None,
        "error": None,
    }


def reset():
    st.session_state.pop("interview", None)


def clear_error():
    st.session_state["interview"]["error"] = None


def end_early():
    iv = st.session_state["interview"]
    iv["total"] = sum(m["role"] == "user" for m in iv["history"])


iv = st.session_state.get("interview")

if iv is None:
    names = {j["id"]: label(j) for j in jobs}
    st.selectbox("Job", list(names), format_func=names.get, key="iv_job")
    st.selectbox("Interview type", list(interviewer.STYLES), key="iv_kind")
    st.slider("Number of questions", 3, 8, 5, key="iv_total")
    st.button("Start interview", type="primary", on_click=start)
    st.stop()

history = iv["history"]
answered = sum(m["role"] == "user" for m in history)

st.caption(f"{iv['label']} | {iv['kind']} | question {min(answered + 1, iv['total'])} of {iv['total']}")
for message in history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

needs_question = answered < iv["total"] and (not history or history[-1]["role"] == "user")
needs_feedback = answered >= iv["total"] and iv["feedback"] is None

if iv["error"]:
    st.error(iv["error"])
    st.button("Try again", on_click=clear_error)
elif needs_question:
    with st.chat_message("assistant"):
        with st.spinner("Thinking of a question..."):
            try:
                question = interviewer.next_question(iv["system"], history)
            except RuntimeError as e:
                iv["error"] = str(e)
            else:
                history.append({"role": "assistant", "content": question})
    st.rerun()
elif needs_feedback:
    with st.spinner("Writing your feedback..."):
        try:
            iv["feedback"] = interviewer.get_feedback(
                db.get_job(iv["job_id"]), interviewer.pairs(history))
        except RuntimeError as e:
            iv["error"] = str(e)
    st.rerun()
elif iv["feedback"] is None:
    answer = st.chat_input("Your answer")
    if answer and answer.strip():
        history.append({"role": "user", "content": answer.strip()[:4000]})
        st.rerun()
    st.button("End now and get feedback", on_click=end_early, disabled=answered == 0)

feedback = iv["feedback"]
if feedback:
    st.divider()
    st.subheader("Feedback")
    st.write(feedback["summary"])
    left, right = st.columns(2)
    with left:
        st.markdown("**Strengths**")
        for item in feedback["strengths"]:
            st.write(f"- {item}")
    with right:
        st.markdown("**To improve**")
        for item in feedback["improvements"]:
            st.write(f"- {item}")
    for i, ((question, _), result) in enumerate(zip(interviewer.pairs(history), feedback["answers"]), 1):
        rating = "-" if result["rating"] is None else f"{result['rating']}/5"
        st.markdown(f"**Q{i}. {question}**  \nRating: {rating}")
        if result["comment"]:
            st.write(result["comment"])
        if result["better"]:
            st.caption("Stronger answer: " + result["better"])
    st.button("Start a new interview", on_click=reset)