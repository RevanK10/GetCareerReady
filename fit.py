from llm_client import LLMClient
from prompts import FIT_PROMPT


def to_list(value):
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def analyze_fit(resume_text, job_description):
    prompt = FIT_PROMPT.format(resume_text=resume_text, job_description=job_description)
    data = LLMClient().generate_json(prompt)

    if not isinstance(data, dict):
        raise RuntimeError("Model returned JSON, but not an object. Try again.")

    try:
        score = int(float(data.get("score", 0)))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    return {
        "title": str(data.get("title") or ""),
        "company": str(data.get("company") or ""),
        "score": score,
        "summary": str(data.get("summary") or ""),
        "strengths": to_list(data.get("strengths")),
        "gaps": to_list(data.get("gaps")),
        "red_flags": to_list(data.get("red_flags")),
    }