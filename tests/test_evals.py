import pytest

from evals.cases import CASES
from evals.run_evals import in_range, run_case


@pytest.mark.parametrize("expect, score, ok", [
    ("high", 65, True), ("high", 64, False), ("low", 40, True), ("low", 41, False)])
def test_in_range(expect, score, ok):
    assert in_range(expect, score) is ok


def test_run_case_scores_and_flags_invented_numbers():
    case = {"id": "x", "resume": "Led a team", "job": "j", "expect": "high"}
    result = run_case(case, lambda r, j: {"score": 80},
                      lambda r, j: {"resume": "Led a team of 12"})
    assert result["ok"] and result["invented"] == ["12"]


def test_run_case_reports_errors_instead_of_crashing():
    def boom(resume, job):
        raise RuntimeError("model down")

    result = run_case({"id": "x", "resume": "r", "job": "j", "expect": "low"}, boom)
    assert not result["ok"] and result["error"] == "model down"


def test_dataset_is_well_formed():
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert all(c["expect"] in ("high", "low") and c["resume"] and c["job"] for c in CASES)
