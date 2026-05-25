from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from incident_agent_eval.config import get_settings
from incident_agent_eval.runbooks import search_markdown_runbooks


def _root() -> Path:
    return get_settings().project_root


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _within_window(row: dict[str, Any], minutes: int) -> bool:
    event_ts = _parse_ts(row["timestamp"])
    anchor = datetime(2026, 5, 24, 14, 30, tzinfo=timezone.utc)
    delta_minutes = (anchor - event_ts).total_seconds() / 60
    return 0 <= delta_minutes <= minutes


def get_service_metrics(service_name: str, time_window_minutes: int) -> list[dict[str, Any]]:
    rows = _read_jsonl(_root() / "data/mock_observability/metrics.jsonl")
    return [
        row
        for row in rows
        if row["service"] == service_name and _within_window(row, time_window_minutes)
    ]


def search_logs(service_name: str, query: str, time_window_minutes: int) -> list[dict[str, Any]]:
    rows = _read_jsonl(_root() / "data/mock_observability/logs.jsonl")
    terms = [term.lower() for term in query.split() if len(term) > 2]
    results = []
    for row in rows:
        if row["service"] != service_name or not _within_window(row, time_window_minutes):
            continue
        haystack = f"{row.get('level', '')} {row.get('message', '')}".lower()
        if not terms or any(term in haystack for term in terms):
            results.append(row)
    return results


def get_recent_deploys(service_name: str, time_window_minutes: int) -> list[dict[str, Any]]:
    rows = _read_jsonl(_root() / "data/mock_observability/deploys.jsonl")
    return [
        row
        for row in rows
        if row["service"] == service_name and _within_window(row, time_window_minutes)
    ]


def get_service_owner(service_name: str) -> dict[str, Any]:
    owners = json.loads((_root() / "data/mock_observability/service_owners.json").read_text(encoding="utf-8"))
    return owners.get(service_name, {"team": "unknown", "escalation": "unknown", "slack": "unknown"})


def search_runbooks(query: str) -> list[dict[str, str | int]]:
    return search_markdown_runbooks(_root() / "data/runbooks", query)


def classify_severity(incident_context: dict[str, Any]) -> dict[str, str]:
    text = " ".join(
        [
            incident_context.get("summary", ""),
            " ".join(incident_context.get("symptoms", [])),
            json.dumps(incident_context.get("metrics", [])),
            json.dumps(incident_context.get("logs", [])),
        ]
    ).lower()
    if ("customer-facing outage" in text and "no customer-facing outage" not in text) or "global outage" in text:
        return {"severity": "SEV-1", "explanation": "Customer-facing outage language indicates SEV-1."}
    if "5xx" in text and ("14%" in text or "crashloopbackoff" in text or "latency" in text):
        return {"severity": "SEV-2", "explanation": "Material production impact with elevated errors, latency, or pod failures."}
    if "crashloopbackoff" in text:
        return {"severity": "SEV-2", "explanation": "Service instability after config change requires urgent response."}
    if "backlog" in text or "slowness" in text or "saturation" in text:
        return {"severity": "SEV-3", "explanation": "Degraded async processing without confirmed customer-facing outage."}
    return {"severity": "SEV-4", "explanation": "Low impact or informational incident."}
