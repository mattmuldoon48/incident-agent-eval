from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from incident_agent_eval.config import get_settings
from incident_agent_eval.llm_client import (
    TRIAGE_PROMPT_VERSION,
    estimate_report_cost,
    generate_triage_report,
    prompt_sha256,
)
from incident_agent_eval.metrics import Timer
from incident_agent_eval.safety import validate_final_report
from incident_agent_eval.schemas import AgentTrace, IncidentInput, SafetyCheck, ToolCall
from incident_agent_eval.tool_registry import READ_ONLY_TOOLS, assert_read_only_registry
from incident_agent_eval.trace import make_trace_id, save_trace, utc_now


def _summarize_result(result: Any) -> str:
    if isinstance(result, list):
        return f"{len(result)} records returned"
    if isinstance(result, dict):
        keys = ", ".join(list(result.keys())[:5])
        return f"object with keys: {keys}"
    return str(result)[:160]


def _call_tool(tool_name: str, func: Callable[..., Any], **kwargs: Any) -> tuple[Any, ToolCall]:
    started = utc_now()
    try:
        result = func(**kwargs)
        return result, ToolCall(
            tool_name=tool_name,
            args=kwargs,
            result_summary=_summarize_result(result),
            started_at=started,
            completed_at=utc_now(),
            success=True,
        )
    except Exception as exc:
        return None, ToolCall(
            tool_name=tool_name,
            args=kwargs,
            result_summary="tool failed",
            started_at=started,
            completed_at=utc_now(),
            success=False,
            error=str(exc),
        )


def run_agent(
    incident_path: str | Path,
    prompt_version: str = TRIAGE_PROMPT_VERSION,
    use_openai: bool = True,
) -> tuple[AgentTrace, Path]:
    assert_read_only_registry()
    settings = get_settings()
    started = utc_now()
    with Timer() as timer:
        incident = IncidentInput.model_validate_json(Path(incident_path).read_text(encoding="utf-8"))
        tool_calls: list[ToolCall] = []

        metrics, call = _call_tool("get_service_metrics", READ_ONLY_TOOLS["get_service_metrics"], service_name=incident.service, time_window_minutes=90)
        tool_calls.append(call)
        deploys, call = _call_tool("get_recent_deploys", READ_ONLY_TOOLS["get_recent_deploys"], service_name=incident.service, time_window_minutes=90)
        tool_calls.append(call)
        logs, call = _call_tool(
            "search_logs",
            READ_ONLY_TOOLS["search_logs"],
            service_name=incident.service,
            query=f"{incident.summary} {' '.join(incident.symptoms)}",
            time_window_minutes=90,
        )
        tool_calls.append(call)
        runbooks, call = _call_tool("search_runbooks", READ_ONLY_TOOLS["search_runbooks"], query=f"{incident.summary} {' '.join(incident.symptoms)}")
        tool_calls.append(call)
        owner, call = _call_tool("get_service_owner", READ_ONLY_TOOLS["get_service_owner"], service_name=incident.service)
        tool_calls.append(call)

        severity_context = {
            **incident.model_dump(mode="json"),
            "metrics": metrics or [],
            "logs": logs or [],
            "deploys": deploys or [],
        }
        severity, call = _call_tool("classify_severity", READ_ONLY_TOOLS["classify_severity"], incident_context=severity_context)
        tool_calls.append(call)

        context = {
            "incident": incident.model_dump(mode="json"),
            "metrics": metrics or [],
            "deploys": deploys or [],
            "logs": logs or [],
            "runbooks": runbooks or [],
            "owner": owner or {},
            "severity": severity or {"severity": "SEV-4", "explanation": "Severity classifier failed."},
            "tools_used": [call.tool_name for call in tool_calls if call.success],
        }
        prompt_hash = prompt_sha256(prompt_version)
        report, usage, used_openai = generate_triage_report(context, prompt_version=prompt_version, use_openai=use_openai)
        safety_result = validate_final_report(report.model_dump())
        if not safety_result["safe"]:
            report.safety_notes.append(f"Safety checker flagged forbidden actions: {safety_result['violations']}")

    completed = utc_now()
    trace = AgentTrace(
        trace_id=make_trace_id(),
        incident_id=incident.id,
        started_at=started,
        completed_at=completed,
        model=settings.openai_model,
        prompt_version=prompt_version,
        prompt_sha256=prompt_hash,
        used_openai=used_openai,
        tool_calls=tool_calls,
        final_report=report,
        safety_check=SafetyCheck.model_validate(safety_result),
        estimated_cost_usd=estimate_report_cost(settings.openai_model, usage),
        latency_ms=timer.elapsed_ms,
    )
    trace_path = save_trace(trace)
    return trace, trace_path


def load_incident(path: str | Path) -> IncidentInput:
    return IncidentInput.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
