from llm_client import LLMClient
from prompts import FEEDBACK_PROMPT, INTERVIEWER_SYSTEM

MAX_CHARS = 6000
STYLES = {
    "Behavioral": "Behavioral questions about past situations: what happened, what you did, the result.",
    "Technical": "Technical questions on the skills and tools the job needs. Ask about concrete problems, not definitions.",
    "Mixed": "Alternate between behavioral and technical questions.",
}


def build_system(job, resume_text, kind):
    return INTERVIEWER_SYSTEM.format(
        kind=kind.lower(),
        style=STYLES[kind],
        title=job["title"] or "the role",
        company=job["company"] or "the company",
        job=job["description"][:MAX_CHARS],
        resume=resume_text[:MAX_CHARS],
    )


def next_question(system, history):
    """history is a list of {"role": "assistant" | "user", "content": ...}, oldest first."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "I'm ready. Please begin."},
        *history,
    ]
    return LLMClient().chat(messages, temperature=0.6).strip()


def pairs(history):
    """Answered questions only: [(question, answer), ...]."""
    found = []
    for i in range(len(history) - 1):
        if history[i]["role"] == "assistant" and history[i + 1]["role"] == "user":
            found.append((history[i]["content"], history[i + 1]["content"]))
    return found


def _rating(value):
    try:
        return max(1, min(5, int(float(value))))
    except (TypeError, ValueError):
        return None


def _strings(value, limit):
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()][:limit]


def get_feedback(job, qa_pairs):
    if not qa_pairs:
        raise RuntimeError("Answer at least one question first.")
    transcript = "\n\n".join(f"Q{i}: {q}\nA{i}: {a}" for i, (q, a) in enumerate(qa_pairs, 1))
    prompt = FEEDBACK_PROMPT.format(
        title=job["title"] or "the role",
        company=job["company"] or "the company",
        job=job["description"][:MAX_CHARS],
        transcript=transcript,
    )
    data = LLMClient().generate_json(prompt)
    if not isinstance(data, dict):
        raise RuntimeError("The coach returned an unexpected format. Try again.")

    raw = data.get("answers") if isinstance(data.get("answers"), list) else []
    answers = []
    for i in range(len(qa_pairs)):
        item = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
        answers.append({
            "rating": _rating(item.get("rating")),
            "comment": str(item.get("comment") or ""),
            "better": str(item.get("better") or ""),
        })
    return {
        "summary": str(data.get("summary") or ""),
        "strengths": _strings(data.get("strengths"), 3),
        "improvements": _strings(data.get("improvements"), 3),
        "answers": answers,
    }