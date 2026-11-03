from llm_client import LLMClient
from prompts import REVIEW_PROMPT


def review_resume(original, tailored):
    """Ask the model to list claims in the tailored resume that the original doesn't support."""
    prompt = REVIEW_PROMPT.format(original=original, tailored=tailored)
    data = LLMClient().generate_json(prompt)
    if not isinstance(data, dict):
        raise RuntimeError("The reviewer returned an unexpected format.")
    issues = data.get("issues", [])
    if not isinstance(issues, list):
        issues = []
    issues = [str(i).strip() for i in issues if str(i).strip()]
    return {"issues": issues[:8]}