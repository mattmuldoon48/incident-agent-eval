from pathlib import Path

from incident_agent_eval.safety_eval import (
    aggregate_safety_eval_results,
    load_safety_eval_cases,
    score_safety_eval_case,
)
from incident_agent_eval.schemas import SafetyEvalCase

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


def test_safety_eval_does_not_treat_expected_phrase_as_detector_rule() -> None:
    case = SafetyEvalCase(
        id="safety_custom",
        report={"recommended_next_actions": ["perform an undocumented custom action"]},
        expected_safe=False,
        expected_violations=["undocumented custom action"],
    )

    result = score_safety_eval_case(case)

    assert not result.passed
    assert result.actual_safe
    assert result.actual_violations == []
    assert result.missed_violations == ["undocumented custom action"]
