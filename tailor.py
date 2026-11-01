from llm_client import LLMClient
from prompts import NOTES_MARKER, RESUME_PROMPT


def tailor_resume(resume_text, job_description):
    prompt = RESUME_PROMPT.format(
        resume_text=resume_text,
        job_description=job_description,
        marker=NOTES_MARKER,
    )
    reply = LLMClient().generate(prompt)
    resume, _, notes = reply.partition(NOTES_MARKER)
    return {"resume": resume.strip(), "notes": notes.strip()}