from llm_client import LLMClient
from prompts import NOTES_MARKER, RESUME_PROMPT


def tailor_resume(resume_text, job_description, feedback=None):
    prompt = RESUME_PROMPT.format(
        resume_text=resume_text,
        job_description=job_description,
        marker=NOTES_MARKER,
    )
    if feedback:
        problems = "\n".join(f"- {item}" for item in feedback)
        prompt += (
            "\n\nA reviewer found unsupported claims in your previous attempt:\n"
            f"{problems}\n"
            "Rewrite the resume without them. Use only facts from the resume above."
        )
    reply = LLMClient().generate(prompt)
    resume, _, notes = reply.partition(NOTES_MARKER)
    return {"resume": resume.strip(), "notes": notes.strip()}