import json
from pathlib import Path

from incident_agent_eval.agent import run_agent
from incident_agent_eval.schemas import AgentTrace

ROOT = Path(__file__).resolve().parents[1]


def test_run_agent_no_openai_saves_valid_trace() -> None:
    trace, trace_path = run_agent(ROOT / "data/incidents/incident_001.json", use_openai=False)

    assert trace.incident_id == "incident_001"
    assert trace.final_report.severity == "SEV-2"
    assert trace.safety_check.safe
    assert not trace.used_openai
    assert trace_path.exists()

    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    parsed = AgentTrace.model_validate(payload)
    assert parsed.trace_id == trace.trace_id


def test_run_agent_uses_fixed_read_only_tool_order() -> None:
    trace, _trace_path = run_agent(ROOT / "data/incidents/incident_001.json", use_openai=False)

    assert [call.tool_name for call in trace.tool_calls] == [
        "get_service_metrics",
        "get_recent_deploys",
        "search_logs",
        "search_runbooks",
        "get_service_owner",
        "classify_severity",
    ]
    assert all(call.success for call in trace.tool_calls)
