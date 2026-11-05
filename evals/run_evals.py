"""Check scoring quality with the real model:  python -m evals.run_evals [--tailor]

--tailor also rewrites each "high" case's resume and flags numbers that were not in the original.
Results vary between runs, so look at the pass rate, not one case.
"""
import sys

from evals.cases import CASES
from evals.checks import new_numbers

RANGES = {"high": (65, 100), "low": (0, 40)}


def in_range(expect, score):
    low, high = RANGES[expect]
    return low <= score <= high


def run_case(case, analyze, tailor=None):
    result = {"id": case["id"], "expect": case["expect"], "score": None, "ok": False, "invented": [], "error": ""}
    try:
        result["score"] = analyze(case["resume"], case["job"])["score"]
        result["ok"] = in_range(case["expect"], result["score"])
        if tailor and case["expect"] == "high":
            result["invented"] = new_numbers(case["resume"], tailor(case["resume"], case["job"])["resume"])
    except RuntimeError as e:
        result["error"] = str(e)
    return result


def main(argv):
    from fit import analyze_fit
    from llm_client import LLMClient

    try:
        LLMClient()  # fails fast with a clear message when the key is missing
    except RuntimeError as e:
        print(e)
        return 2

    tailor = None
    if "--tailor" in argv:
        from tailor import tailor_resume
        tailor = tailor_resume

    results = [run_case(case, analyze_fit, tailor) for case in CASES]
    for r in results:
        status = "PASS" if r["ok"] else ("ERROR" if r["error"] else "FAIL")
        extra = f"  invented numbers: {r['invented']}" if r["invented"] else ""
        print(f"{status:5} {r['id']:15} expect {r['expect']:5} got {r['score']}{extra}  {r['error']}")
    passed = sum(r["ok"] for r in results)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) and not any(r["invented"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
