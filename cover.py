from llm_client import LLMClient
from prompts import COVER_LETTER_PROMPT


def write_cover_letter(resume_text, job_description, name="", title="", company=""):
    prompt = COVER_LETTER_PROMPT.format(
        name=name or "the candidate",
        resume_text=resume_text,
        title=title or "the role",
        company=company or "the company",
        job_description=job_description,
    )
    return LLMClient().generate(prompt).strip()