from pathlib import Path

from incident_agent_eval.safety_eval import (
    aggregate_safety_eval_results,
    load_safety_eval_cases,
    score_safety_eval_case,
)

ROOT = Path(__file__).resolve().parents[1]


def test_safety_eval_cases_pass_expected_guardrails() -> None:
    cases = load_safety_eval_cases(ROOT / "data/eval_sets/safety_eval_v1.jsonl")

    results = [score_safety_eval_case(case) for case in cases]
    aggregate = aggregate_safety_eval_results(results)

    assert aggregate["case_count"] == 8
    assert aggregate["failed_count"] == 0
    assert aggregate["pass_rate"] == 1.0


def test_safety_eval_records_missed_violation() -> None:
    case = load_safety_eval_cases(ROOT / "data/eval_sets/safety_eval_v1.jsonl")[0]
    case.expected_violations = ["modify IAM"]

    result = score_safety_eval_case(case)

    assert not result.passed
    assert result.missed_violations == ["modify IAM"]
