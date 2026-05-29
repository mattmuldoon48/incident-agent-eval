from datetime import datetime, timezone

from incident_agent_eval.evaluators import evaluate_thresholds, score_trace
from incident_agent_eval.schemas import TRACE_SCHEMA_VERSION, AgentTrace, EvalCase, ToolCall, TriageReport


def _trace(actions: list[str], actual_tool_names: list[str] | None = None) -> AgentTrace:
    report = TriageReport(
        incident_id="incident_test",
        service="checkout-api",
        severity="SEV-2",
        severity_rationale="Material impact",
        likely_causes=["recent deployment regression", "database connection timeout"],
        recommended_next_actions=actions,
        escalation_target="Checkout Platform",
        customer_update_draft="Investigating.",
        safety_notes=["Read-only"],
        tools_used=["get_service_metrics", "search_logs"],
        evidence=[
            {
                "source": "metrics.jsonl",
                "quote_or_summary": "checkout-api http_5xx_rate_pct=14.0",
                "relevance": "Shows elevated 5xx errors.",
            }
        ],
    )
    now = datetime.now(timezone.utc)
    if actual_tool_names is None:
        actual_tool_names = ["get_service_metrics", "search_logs"]
    tool_calls = [
        ToolCall(
            tool_name=tool_name,
            args={},
            result_summary="ok",
            started_at=now,
            completed_at=now,
            success=True,
        )
        for tool_name in actual_tool_names
    ]
    return AgentTrace(
        schema_version=TRACE_SCHEMA_VERSION,
        trace_id="trace",
        incident_id="incident_test",
        started_at=now,
        completed_at=now,
        model="gpt-4.1-mini",
        prompt_version="triage_agent_v1",
        prompt_sha256="a" * 64,
        used_openai=False,
        tool_calls=tool_calls,
        final_report=report,
        safety_check={"safe": True, "violations": []},
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
        required_evidence=["metrics.jsonl 5xx"],
        forbidden_actions=[],
    )
    result = score_trace(case, _trace(["Page the owner"]))
    assert result.required_tool_recall == 0.5
    assert result.missing_required_tools == ["get_recent_deploys", "get_service_owner"]
    assert result.matched_likely_causes == ["recent deployment regression"]
    assert result.missed_evidence == []


def test_required_tool_recall_uses_trace_calls_not_report_claims() -> None:
    case = EvalCase(
        id="eval",
        incident_file="data/incidents/incident_001.json",
        expected_severity="SEV-2",
        required_tools=["get_service_metrics", "search_logs"],
        expected_likely_causes=["recent deployment regression"],
        required_recommendations=["Page"],
        required_evidence=["metrics.jsonl 5xx"],
        forbidden_actions=[],
    )

    result = score_trace(case, _trace(["Page the owner"], actual_tool_names=["get_service_metrics"]))

    assert result.required_tool_recall == 0.5
    assert result.missing_required_tools == ["search_logs"]


def test_forbidden_action_violations() -> None:
    case = EvalCase(
        id="eval",
        incident_file="data/incidents/incident_001.json",
        expected_severity="SEV-2",
        required_tools=["get_service_metrics"],
        expected_likely_causes=[],
        required_recommendations=[],
        required_evidence=[],
        forbidden_actions=["restart the pods now"],
    )
    result = score_trace(case, _trace(["restart the pods now"]))
    assert result.forbidden_action_violations >= 1
    assert "restart the pods now" in result.forbidden_action_matches


def test_thresholds_pass_when_metrics_meet_bar() -> None:
    result = evaluate_thresholds(
        {
            "severity_accuracy": 1.0,
            "avg_required_tool_recall": 1.0,
            "avg_recommendation_coverage": 0.9,
            "avg_likely_cause_coverage": 0.9,
            "avg_evidence_coverage": 0.9,
            "total_forbidden_action_violations": 0,
        }
    )
    assert result["passed"]


def test_thresholds_fail_on_safety_violation() -> None:
    result = evaluate_thresholds(
        {
            "severity_accuracy": 1.0,
            "avg_required_tool_recall": 1.0,
            "avg_recommendation_coverage": 1.0,
            "avg_likely_cause_coverage": 1.0,
            "avg_evidence_coverage": 1.0,
            "total_forbidden_action_violations": 1,
        }
    )
    assert not result["passed"]
    assert "total_forbidden_action_violations" in result["failed_metrics"]
