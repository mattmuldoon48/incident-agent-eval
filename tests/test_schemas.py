import pytest
from pydantic import ValidationError

from incident_agent_eval.schemas import (
    AgentTrace,
    EvalResult,
    EvidenceItem,
    IncidentInput,
    ToolCall,
    TriageReport,
)


def test_incident_input_validates() -> None:
    incident = IncidentInput(
        id="incident_test",
        service="checkout-api",
        summary="Elevated errors",
        symptoms=["5xx increased"],
        started_at="2026-05-24T14:05:00Z",
    )
    assert incident.service == "checkout-api"


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", ""), ("service", ""), ("summary", ""), ("symptoms", [])],
)
def test_incident_input_rejects_empty_required_fields(field, value) -> None:
    payload = {
        "id": "incident_test",
        "service": "checkout-api",
        "summary": "Elevated errors",
        "symptoms": ["5xx increased"],
        "started_at": "2026-05-24T14:05:00Z",
    }
    payload[field] = value

    with pytest.raises(ValidationError, match="at least 1"):
        IncidentInput(**payload)


def test_incident_input_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        IncidentInput(
            id="incident_test",
            service="checkout-api",
            summary="Elevated errors",
            symptoms=["5xx increased"],
            started_at="2026-05-24T14:05:00Z",
            owner="Checkout Platform",
        )


def test_tool_call_rejects_completion_before_start() -> None:
    with pytest.raises(ValidationError, match="completed_at must not precede started_at"):
        ToolCall(
            tool_name="search_logs",
            args={},
            result_summary="No matching errors",
            started_at="2026-05-24T14:06:00Z",
            completed_at="2026-05-24T14:05:00Z",
            success=True,
        )


def test_agent_trace_rejects_completion_before_start() -> None:
    with pytest.raises(ValidationError, match="completed_at must not precede started_at"):
        AgentTrace(
            trace_id="trace_test",
            incident_id="incident_test",
            started_at="2026-05-24T14:06:00Z",
            completed_at="2026-05-24T14:05:00Z",
            model="gpt-4.1-mini",
            prompt_version="triage_agent_v1",
            prompt_sha256="a" * 64,
            used_openai=False,
            tool_calls=[],
            final_report={
                "incident_id": "incident_test",
                "service": "checkout-api",
                "severity": "SEV-2",
                "severity_rationale": "Material impact",
                "likely_causes": ["recent deployment regression"],
                "evidence": [],
                "recommended_next_actions": ["Page the owner"],
                "escalation_target": "Checkout Platform",
                "customer_update_draft": "We are investigating.",
                "safety_notes": ["Read-only"],
                "tools_used": [],
            },
            safety_check={"safe": True, "violations": []},
            estimated_cost_usd=0,
            latency_ms=0,
        )


def test_triage_report_validates() -> None:
    report = TriageReport(
        incident_id="incident_test",
        service="checkout-api",
        severity="SEV-2",
        severity_rationale="Material impact",
        likely_causes=["recent deployment regression"],
        evidence=[EvidenceItem(source="logs", quote_or_summary="timeout", relevance="matches symptom")],
        recommended_next_actions=["Page the owner"],
        escalation_target="Checkout Platform",
        customer_update_draft="We are investigating.",
        safety_notes=["Read-only"],
        tools_used=["search_logs"],
    )
    assert report.severity == "SEV-2"


def test_triage_report_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError, match="String should match pattern"):
        TriageReport(
            incident_id="incident_test",
            service="checkout-api",
            severity="SEV-5",
            severity_rationale="Outside supported severity scale",
            likely_causes=["recent deployment regression"],
            evidence=[EvidenceItem(source="logs", quote_or_summary="timeout", relevance="matches symptom")],
            recommended_next_actions=["Page the owner"],
            escalation_target="Checkout Platform",
            customer_update_draft="We are investigating.",
            safety_notes=["Read-only"],
            tools_used=["search_logs"],
        )


def test_evidence_item_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EvidenceItem(
            source="logs",
            quote_or_summary="database timeout",
            relevance="matches symptom",
            confidence=0.9,
        )


@pytest.mark.parametrize("incident_id", ["../escaped", "nested/path", "nested\\path"])
def test_incident_input_rejects_path_like_identifiers(incident_id: str) -> None:
    with pytest.raises(ValidationError, match="String should match pattern"):
        IncidentInput(
            id=incident_id,
            service="checkout-api",
            summary="Elevated errors",
            symptoms=["5xx increased"],
            started_at="2026-05-24T14:05:00Z",
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("severity_correct", 2),
        ("required_tool_recall", 1.1),
        ("recommendation_coverage", -0.1),
        ("likely_cause_coverage", 1.1),
        ("evidence_coverage", -0.1),
        ("forbidden_action_violations", -1),
        ("latency_ms", -1),
        ("estimated_cost_usd", -0.01),
        ("estimated_cost_usd", float("inf")),
        ("estimated_cost_usd", float("nan")),
    ],
)
def test_eval_result_rejects_invalid_metrics(
    field_name: str,
    invalid_value: int | float,
) -> None:
    payload = {
        "eval_case_id": "eval_test",
        "severity_correct": 1,
        "required_tool_recall": 1.0,
        "recommendation_coverage": 1.0,
        "likely_cause_coverage": 1.0,
        "evidence_coverage": 1.0,
        "forbidden_action_violations": 0,
        "latency_ms": 100,
        "estimated_cost_usd": 0.01,
    }
    payload[field_name] = invalid_value

    with pytest.raises(ValidationError):
        EvalResult(**payload)
