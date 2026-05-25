from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from incident_agent_eval.config import get_settings
from incident_agent_eval.schemas import AgentTrace


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_trace_id() -> str:
    return str(uuid4())


def model_dump_jsonable(model: BaseModel) -> dict:
    return json.loads(model.model_dump_json())


def save_trace(trace: AgentTrace) -> Path:
    root = get_settings().project_root
    trace_dir = root / "reports/traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    timestamp = trace.started_at.strftime("%Y%m%dT%H%M%SZ")
    path = trace_dir / f"{trace.incident_id}_{timestamp}.json"
    payload = model_dump_jsonable(trace)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
