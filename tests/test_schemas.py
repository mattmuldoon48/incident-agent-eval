import pytest
from pydantic import ValidationError

from incident_agent_eval.schemas import EvidenceItem, IncidentInput, TriageReport


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
