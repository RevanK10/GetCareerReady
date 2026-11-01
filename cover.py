from llm_client import LLMClient
from prompts import COVER_PROMPT


def write_cover_letter(resume_text, job_description, name=""):
    prompt = COVER_PROMPT.format(
        name=name or "the candidate",
        resume_text=resume_text,
        job_description=job_description,
    )
    return LLMClient().generate(prompt).strip()