from pathlib import Path

import pytest

from incident_agent_eval.eval_sets import load_and_validate_eval_cases, validate_eval_cases
from incident_agent_eval.schemas import EvalCase

ROOT = Path(__file__).resolve().parents[1]


def _case(**overrides) -> EvalCase:
    data = {
        "id": "eval_test",
        "incident_file": "data/incidents/incident_001.json",
        "expected_severity": "SEV-2",
        "required_tools": ["get_service_metrics", "search_logs"],
        "expected_likely_causes": ["database connection timeout"],
        "required_recommendations": ["Page the Checkout Platform"],
        "required_evidence": ["metrics.jsonl 5xx"],
        "forbidden_actions": ["restart pods"],
    }
    data.update(overrides)
    return EvalCase(**data)


def test_validate_eval_cases_accepts_valid_case() -> None:
    assert validate_eval_cases([_case()], ROOT) == []


def test_validate_eval_cases_rejects_unknown_tool() -> None:
    errors = validate_eval_cases([_case(required_tools=["restart_pods"])], ROOT)
    assert "unknown required tools" in errors[0]



def test_validate_eval_cases_rejects_empty_required_fields() -> None:
    errors = validate_eval_cases([_case(required_tools=[], required_evidence=[])], ROOT)

    assert any("required_tools must not be empty" in error for error in errors)
    assert any("required_evidence must not be empty" in error for error in errors)

def test_validate_eval_cases_rejects_missing_incident_file() -> None:
    errors = validate_eval_cases([_case(incident_file="data/incidents/missing.json")], ROOT)
    assert "incident file does not exist" in errors[0]


def test_validate_eval_cases_rejects_malformed_incident_json(tmp_path: Path) -> None:
    incident_file = "data/incidents/malformed.json"
    incident_path = tmp_path / incident_file
    incident_path.parent.mkdir(parents=True)
    incident_path.write_text("{not-json", encoding="utf-8")

    errors = validate_eval_cases(
        [_case(id="eval_malformed", incident_file=incident_file)], tmp_path
    )

    assert len(errors) == 1
    assert "eval_malformed" in errors[0]
    assert incident_file in errors[0]
    assert "Invalid JSON" in errors[0]


def test_validate_eval_cases_rejects_schema_invalid_incident_json(
    tmp_path: Path,
) -> None:
    incident_file = "data/incidents/schema_invalid.json"
    incident_path = tmp_path / incident_file
    incident_path.parent.mkdir(parents=True)
    incident_path.write_text(
        """{
            "id": "incident_invalid",
            "service": "checkout-api",
            "summary": "Elevated errors",
            "symptoms": ["HTTP 500 rate increased"],
            "started_at": "2025-01-15T10:00:00Z",
            "unexpected": true
        }""",
        encoding="utf-8",
    )

    errors = validate_eval_cases(
        [_case(id="eval_schema_invalid", incident_file=incident_file)], tmp_path
    )

    assert len(errors) == 1
    assert "eval_schema_invalid" in errors[0]
    assert incident_file in errors[0]
    assert "Extra inputs are not permitted" in errors[0]


def test_validate_eval_cases_rejects_duplicate_ids() -> None:
    errors = validate_eval_cases([_case(), _case()], ROOT)
    assert any("duplicate eval case id" in error for error in errors)


def test_load_and_validate_eval_cases_raises_for_invalid_eval_set(tmp_path: Path) -> None:
    path = tmp_path / "bad_eval.jsonl"
    path.write_text(
        _case(required_tools=["restart_pods"]).model_dump_json() + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid eval set"):
        load_and_validate_eval_cases(path, ROOT)
