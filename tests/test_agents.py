import json

import pytest

import cover
import fit
import interviewer
import review
import tailor
from prompts import NOTES_MARKER


# fit

def test_fit_clamps_score_and_cleans_fields(fake_llm):
    fake_llm.json_default = {"score": "150", "title": None, "strengths": "oops", "gaps": ["a", 1]}
    result = fit.analyze_fit("resume", "job")
    assert result["score"] == 100
    assert result["title"] == ""
    assert result["strengths"] == []
    assert result["gaps"] == ["a", "1"]


@pytest.mark.parametrize("raw, expected", [("abc", 0), (-5, 0), (None, 0), (72.9, 72)])
def test_fit_score_edge_cases(fake_llm, raw, expected):
    fake_llm.json_default = {"score": raw}
    assert fit.analyze_fit("r", "j")["score"] == expected


def test_fit_rejects_non_object(fake_llm):
    fake_llm.json_default = [1, 2]
    with pytest.raises(RuntimeError):
        fit.analyze_fit("r", "j")


# tailor

def test_tailor_splits_resume_and_notes(fake_llm):
    fake_llm.text_default = f"# Jane\n{NOTES_MARKER}\n- changed x"
    assert tailor.tailor_resume("r", "j") == {"resume": "# Jane", "notes": "- changed x"}


def test_tailor_survives_missing_marker(fake_llm):
    fake_llm.text_default = "# Jane only"
    assert tailor.tailor_resume("r", "j") == {"resume": "# Jane only", "notes": ""}


def test_tailor_feedback_is_added_to_prompt(fake_llm):
    tailor.tailor_resume("r", "j")
    tailor.tailor_resume("r", "j", ["Invented a PhD"])
    assert "reviewer" not in fake_llm.prompts[0]
    assert "- Invented a PhD" in fake_llm.prompts[1]


# cover
def test_cover_uses_details_or_fallbacks(fake_llm):
    assert cover.write_cover_letter("r", "j", "Jane", "Data Engineer", "Acme") == "stub reply"
    cover.write_cover_letter("r", "j")
    assert "Jane" in fake_llm.prompts[0] and "Data Engineer at Acme" in fake_llm.prompts[0]
    assert "the candidate" in fake_llm.prompts[1] and "the role at the company" in fake_llm.prompts[1]


# review

def test_review_cleans_issues(fake_llm):
    fake_llm.json_default = {"issues": ["fake PhD", " ", 3]}
    assert review.review_resume("o", "t") == {"issues": ["fake PhD", "3"]}


def test_review_handles_bad_shapes(fake_llm):
    fake_llm.json_default = {"issues": "oops"}
    assert review.review_resume("o", "t") == {"issues": []}
    fake_llm.json_default = [1]
    with pytest.raises(RuntimeError):
        review.review_resume("o", "t")


# interviewer

def test_interview_messages_start_with_system_then_user(fake_llm):
    job = {"title": "Eng", "company": "Acme", "description": "d"}
    system = interviewer.build_system(job, "resume", "Mixed")
    interviewer.next_question(system, [])
    roles = [m["role"] for m in fake_llm.messages[0]]
    assert roles == ["system", "user"]
    history = [{"role": "assistant", "content": "Q1"}, {"role": "user", "content": "A1"}]
    interviewer.next_question(system, history)
    assert [m["role"] for m in fake_llm.messages[1]] == ["system", "user", "assistant", "user"]


def test_interview_pairs_skip_unanswered_questions():
    history = [
        {"role": "assistant", "content": "Q1"}, {"role": "user", "content": "A1"},
        {"role": "assistant", "content": "Q2"},
    ]
    assert interviewer.pairs(history) == [("Q1", "A1")]


def test_interview_feedback_is_normalised(fake_llm):
    job = {"title": "", "company": "", "description": "d"}
    fake_llm.json_default = {"summary": "ok", "strengths": ["a", "", "b"], "improvements": "x",
                             "answers": [{"rating": "9", "comment": "c"}, "junk"]}
    result = interviewer.get_feedback(job, [("q1", "a1"), ("q2", "a2"), ("q3", "a3")])
    assert result["strengths"] == ["a", "b"]
    assert result["improvements"] == []
    assert [a["rating"] for a in result["answers"]] == [5, None, None]


def test_interview_feedback_needs_answers(fake_llm):
    with pytest.raises(RuntimeError):
        interviewer.get_feedback({"title": "", "company": "", "description": "d"}, [])
