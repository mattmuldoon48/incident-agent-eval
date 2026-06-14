from __future__ import annotations

from pathlib import Path

import pytest

from incident_agent_eval import langgraph_runner
from incident_agent_eval.schemas import TriageReport
from incident_agent_eval.tool_registry import MUTATING_TOOL_KEYWORDS, READ_ONLY_TOOLS

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TOOL_NAMES = [
    "get_service_metrics",
    "get_recent_deploys",
    "search_logs",
    "search_runbooks",
    "get_service_owner",
    "classify_severity",
]
REQUIRED_STATE_FIELDS = {
    "incident",
    "metrics_result",
    "deploy_result",
    "log_result",
    "runbook_result",
    "owner_result",
    "severity_result",
    "final_report",
    "safety_result",
    "tool_calls",
    "errors",
}


def test_build_langgraph_workflow_when_extra_is_installed() -> None:
    pytest.importorskip("langgraph")

    graph = langgraph_runner.build_langgraph_workflow()

    assert graph is not None


def test_langgraph_state_contains_required_fields_without_langgraph_dependency() -> None:
    state = _state_after_safety_check()

    assert REQUIRED_STATE_FIELDS <= state.keys()
    assert [call.tool_name for call in state["tool_calls"]] == REQUIRED_TOOL_NAMES
    assert state["safety_result"]["safe"]


def test_langgraph_runner_reuses_read_only_tool_registry() -> None:
    assert langgraph_runner.READ_ONLY_TOOLS is READ_ONLY_TOOLS

    for tool_name in REQUIRED_TOOL_NAMES:
        assert tool_name in langgraph_runner.READ_ONLY_TOOLS


def test_langgraph_runner_introduces_no_mutating_tools() -> None:
    bad_tools = [
        name
        for name in langgraph_runner.READ_ONLY_TOOLS
        if any(keyword in name for keyword in MUTATING_TOOL_KEYWORDS)
    ]

    assert bad_tools == []


def test_safety_check_node_runs_and_records_violations() -> None:
    report = TriageReport(
        incident_id="incident_test",
        service="checkout-api",
        severity="SEV-2",
        severity_rationale="Material impact.",
        likely_causes=["deployment regression"],
        evidence=[],
        recommended_next_actions=["restart pods"],
        escalation_target="Checkout Platform",
        customer_update_draft="Investigating.",
        safety_notes=[],
        tools_used=[],
    )

    result = langgraph_runner.safety_check_node({"final_report": report})

    assert result["safety_result"] == {"safe": False, "violations": ["restart pods"]}
    assert "Safety checker flagged forbidden actions" in result["final_report"].safety_notes[-1]


def test_save_trace_marks_langgraph_orchestration_mode() -> None:
    state = _state_after_safety_check()
    state.update(langgraph_runner.save_trace_node(state))

    trace = state["trace"]
    trace_path = state["trace_path"]
    assert trace.orchestration_mode == "langgraph"
    assert trace_path.exists()
    assert '"orchestration_mode": "langgraph"' in trace_path.read_text(encoding="utf-8")


def _state_after_safety_check() -> dict:
    state = {
        "incident_path": str(ROOT / "data/incidents/incident_001.json"),
        "prompt_version": "triage_agent_v1",
        "use_openai": False,
        "started_at": langgraph_runner.utc_now(),
        "timer_started_ns": langgraph_runner.time.perf_counter_ns(),
        "tool_calls": [],
        "errors": [],
    }
    for node in [
        langgraph_runner.load_incident_node,
        langgraph_runner.get_metrics_node,
        langgraph_runner.get_recent_deploys_node,
        langgraph_runner.search_logs_node,
        langgraph_runner.search_runbooks_node,
        langgraph_runner.get_service_owner_node,
        langgraph_runner.classify_severity_node,
        langgraph_runner.generate_report_node,
        langgraph_runner.safety_check_node,
    ]:
        state.update(node(state))
    return state
