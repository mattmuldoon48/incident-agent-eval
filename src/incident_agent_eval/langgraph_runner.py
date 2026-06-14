from __future__ import annotations

import time
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from incident_agent_eval.agent import _call_tool, load_incident
from incident_agent_eval.config import get_settings
from incident_agent_eval.llm_client import (
    TRIAGE_PROMPT_VERSION,
    estimate_report_cost,
    generate_triage_report,
    prompt_sha256,
)
from incident_agent_eval.safety import validate_final_report
from incident_agent_eval.schemas import AgentTrace, IncidentInput, SafetyCheck, ToolCall, TriageReport
from incident_agent_eval.tool_registry import READ_ONLY_TOOLS, assert_read_only_registry
from incident_agent_eval.trace import make_trace_id, save_trace, utc_now

LANGGRAPH_ORCHESTRATION_MODE = "langgraph"


class LangGraphState(TypedDict):
    incident_path: str
    prompt_version: str
    use_openai: bool
    started_at: Any
    timer_started_ns: int
    incident: NotRequired[IncidentInput]
    metrics_result: NotRequired[list[dict[str, Any]]]
    deploy_result: NotRequired[list[dict[str, Any]]]
    log_result: NotRequired[list[dict[str, Any]]]
    runbook_result: NotRequired[list[dict[str, Any]]]
    owner_result: NotRequired[dict[str, Any]]
    severity_result: NotRequired[dict[str, str]]
    final_report: NotRequired[TriageReport]
    safety_result: NotRequired[dict[str, Any]]
    tool_calls: list[ToolCall]
    errors: list[str]
    prompt_hash: NotRequired[str]
    used_openai: NotRequired[bool]
    usage: NotRequired[Any]
    trace: NotRequired[AgentTrace]
    trace_path: NotRequired[Path]


def _missing_langgraph_error() -> ImportError:
    return ImportError(
        "LangGraph orchestration requires the optional extra: "
        'pip install -e ".[langgraph]"'
    )


def _record_tool_result(state: LangGraphState, tool_name: str, result_key: str, **kwargs: Any) -> dict[str, Any]:
    result, call = _call_tool(tool_name, READ_ONLY_TOOLS[tool_name], **kwargs)
    errors = list(state.get("errors", []))
    if call.error:
        errors.append(f"{tool_name}: {call.error}")
    return {
        result_key: result,
        "tool_calls": [*state.get("tool_calls", []), call],
        "errors": errors,
    }


def load_incident_node(state: LangGraphState) -> dict[str, Any]:
    return {"incident": load_incident(state["incident_path"])}


def get_metrics_node(state: LangGraphState) -> dict[str, Any]:
    incident = state["incident"]
    return _record_tool_result(
        state,
        "get_service_metrics",
        "metrics_result",
        service_name=incident.service,
        time_window_minutes=90,
    )


def get_recent_deploys_node(state: LangGraphState) -> dict[str, Any]:
    incident = state["incident"]
    return _record_tool_result(
        state,
        "get_recent_deploys",
        "deploy_result",
        service_name=incident.service,
        time_window_minutes=90,
    )


def search_logs_node(state: LangGraphState) -> dict[str, Any]:
    incident = state["incident"]
    return _record_tool_result(
        state,
        "search_logs",
        "log_result",
        service_name=incident.service,
        query=f"{incident.summary} {' '.join(incident.symptoms)}",
        time_window_minutes=90,
    )


def search_runbooks_node(state: LangGraphState) -> dict[str, Any]:
    incident = state["incident"]
    return _record_tool_result(
        state,
        "search_runbooks",
        "runbook_result",
        query=f"{incident.summary} {' '.join(incident.symptoms)}",
    )


def get_service_owner_node(state: LangGraphState) -> dict[str, Any]:
    incident = state["incident"]
    return _record_tool_result(
        state,
        "get_service_owner",
        "owner_result",
        service_name=incident.service,
    )


def classify_severity_node(state: LangGraphState) -> dict[str, Any]:
    incident = state["incident"]
    severity_context = {
        **incident.model_dump(mode="json"),
        "metrics": state.get("metrics_result") or [],
        "logs": state.get("log_result") or [],
        "deploys": state.get("deploy_result") or [],
    }
    return _record_tool_result(
        state,
        "classify_severity",
        "severity_result",
        incident_context=severity_context,
    )


def _report_context(state: LangGraphState) -> dict[str, Any]:
    incident = state["incident"]
    tool_calls = state.get("tool_calls", [])
    return {
        "incident": incident.model_dump(mode="json"),
        "metrics": state.get("metrics_result") or [],
        "deploys": state.get("deploy_result") or [],
        "logs": state.get("log_result") or [],
        "runbooks": state.get("runbook_result") or [],
        "owner": state.get("owner_result") or {},
        "severity": state.get("severity_result")
        or {"severity": "SEV-4", "explanation": "Severity classifier failed."},
        "tools_used": [call.tool_name for call in tool_calls if call.success],
    }


def generate_report_node(state: LangGraphState) -> dict[str, Any]:
    prompt_version = state["prompt_version"]
    prompt_hash = prompt_sha256(prompt_version)
    report, usage, used_openai = generate_triage_report(
        _report_context(state),
        prompt_version=prompt_version,
        use_openai=state["use_openai"],
    )
    return {"final_report": report, "usage": usage, "used_openai": used_openai, "prompt_hash": prompt_hash}


def safety_check_node(state: LangGraphState) -> dict[str, Any]:
    report = state["final_report"]
    safety_result = validate_final_report(report.model_dump())
    if not safety_result["safe"]:
        report.safety_notes.append(
            f"Safety checker flagged forbidden actions: {safety_result['violations']}"
        )
    return {"final_report": report, "safety_result": safety_result}


def save_trace_node(state: LangGraphState) -> dict[str, Any]:
    settings = get_settings()
    completed = utc_now()
    elapsed_ns = time.perf_counter_ns() - state["timer_started_ns"]
    trace = AgentTrace(
        orchestration_mode=LANGGRAPH_ORCHESTRATION_MODE,
        trace_id=make_trace_id(),
        incident_id=state["incident"].id,
        started_at=state["started_at"],
        completed_at=completed,
        model=settings.openai_model,
        prompt_version=state["prompt_version"],
        prompt_sha256=state["prompt_hash"],
        used_openai=state["used_openai"],
        tool_calls=state.get("tool_calls", []),
        final_report=state["final_report"],
        safety_check=SafetyCheck.model_validate(state["safety_result"]),
        estimated_cost_usd=estimate_report_cost(settings.openai_model, state["usage"]),
        latency_ms=round(elapsed_ns / 1_000_000),
    )
    trace_path = save_trace(trace)
    return {"trace": trace, "trace_path": trace_path}


def build_langgraph_workflow() -> Any:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise _missing_langgraph_error() from exc

    workflow = StateGraph(LangGraphState)
    workflow.add_node("load_incident", load_incident_node)
    workflow.add_node("get_metrics", get_metrics_node)
    workflow.add_node("get_recent_deploys", get_recent_deploys_node)
    workflow.add_node("search_logs", search_logs_node)
    workflow.add_node("search_runbooks", search_runbooks_node)
    workflow.add_node("get_service_owner", get_service_owner_node)
    workflow.add_node("classify_severity", classify_severity_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("safety_check", safety_check_node)
    workflow.add_node("save_trace", save_trace_node)

    workflow.add_edge(START, "load_incident")
    workflow.add_edge("load_incident", "get_metrics")
    workflow.add_edge("get_metrics", "get_recent_deploys")
    workflow.add_edge("get_recent_deploys", "search_logs")
    workflow.add_edge("search_logs", "search_runbooks")
    workflow.add_edge("search_runbooks", "get_service_owner")
    workflow.add_edge("get_service_owner", "classify_severity")
    workflow.add_edge("classify_severity", "generate_report")
    workflow.add_edge("generate_report", "safety_check")
    workflow.add_edge("safety_check", "save_trace")
    workflow.add_edge("save_trace", END)
    return workflow.compile()


def run_langgraph_agent(
    incident_path: str | Path,
    prompt_version: str = TRIAGE_PROMPT_VERSION,
    use_openai: bool = True,
) -> tuple[AgentTrace, Path]:
    assert_read_only_registry()
    graph = build_langgraph_workflow()
    state = graph.invoke(
        {
            "incident_path": str(incident_path),
            "prompt_version": prompt_version,
            "use_openai": use_openai,
            "started_at": utc_now(),
            "timer_started_ns": time.perf_counter_ns(),
            "tool_calls": [],
            "errors": [],
        }
    )
    return state["trace"], state["trace_path"]
