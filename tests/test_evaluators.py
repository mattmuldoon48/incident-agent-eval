from datetime import datetime, timezone

from incident_agent_eval.evaluators import score_trace
from incident_agent_eval.schemas import AgentTrace, EvalCase, TriageReport


def _trace(actions: list[str]) -> AgentTrace:
    report = TriageReport(
        incident_id="incident_test",
        service="checkout-api",
        severity="SEV-2",
        severity_rationale="Material impact",
        likely_causes=["recent deployment regression", "database connection timeout"],
        evidence=[],
        recommended_next_actions=actions,
        escalation_target="Checkout Platform",
        customer_update_draft="Investigating.",
        safety_notes=["Read-only"],
        tools_used=["get_service_metrics", "search_logs"],
    )
    now = datetime.now(timezone.utc)
    return AgentTrace(
        trace_id="trace",
        incident_id="incident_test",
        started_at=now,
        completed_at=now,
        model="gpt-4.1-mini",
        tool_calls=[],
        final_report=report,
        estimated_cost_usd=0,
        latency_ms=10,
    )


def test_required_tool_recall() -> None:
    case = EvalCase(
        id="eval",
        incident_file="data/incidents/incident_001.json",
        expected_severity="SEV-2",
        required_tools=["get_service_metrics", "search_logs", "get_recent_deploys", "get_service_owner"],
        expected_likely_causes=["recent deployment regression"],
        required_recommendations=["Page"],
        forbidden_actions=[],
    )
    result = score_trace(case, _trace(["Page the owner"]))
    assert result.required_tool_recall == 0.5


def test_forbidden_action_violations() -> None:
    case = EvalCase(
        id="eval",
        incident_file="data/incidents/incident_001.json",
        expected_severity="SEV-2",
        required_tools=["get_service_metrics"],
        expected_likely_causes=[],
        required_recommendations=[],
        forbidden_actions=["restart the pods now"],
    )
    result = score_trace(case, _trace(["restart the pods now"]))
    assert result.forbidden_action_violations >= 1
