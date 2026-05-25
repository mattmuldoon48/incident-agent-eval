from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IncidentInput(StrictBaseModel):
    id: str
    service: str
    summary: str
    symptoms: list[str]
    started_at: datetime


class ToolCall(StrictBaseModel):
    tool_name: str
    args: dict[str, Any]
    result_summary: str
    started_at: datetime
    completed_at: datetime
    success: bool
    error: str | None = None


class EvidenceItem(StrictBaseModel):
    source: str
    quote_or_summary: str
    relevance: str


class TriageReport(StrictBaseModel):
    incident_id: str
    service: str
    severity: str = Field(pattern=r"^SEV-[1-4]$")
    severity_rationale: str
    likely_causes: list[str]
    evidence: list[EvidenceItem]
    recommended_next_actions: list[str]
    escalation_target: str
    customer_update_draft: str
    safety_notes: list[str]
    tools_used: list[str]


class SafetyCheck(StrictBaseModel):
    safe: bool
    violations: list[str]


class AgentTrace(StrictBaseModel):
    trace_id: str
    incident_id: str
    started_at: datetime
    completed_at: datetime
    model: str
    prompt_version: str
    used_openai: bool
    tool_calls: list[ToolCall]
    final_report: TriageReport
    safety_check: SafetyCheck
    estimated_cost_usd: float
    latency_ms: int


class EvalCase(StrictBaseModel):
    id: str
    incident_file: str
    expected_severity: str
    required_tools: list[str]
    expected_likely_causes: list[str]
    required_recommendations: list[str]
    forbidden_actions: list[str]


class EvalResult(StrictBaseModel):
    eval_case_id: str
    severity_correct: int
    required_tool_recall: float
    recommendation_coverage: float
    likely_cause_coverage: float
    forbidden_action_violations: int
    latency_ms: int
    estimated_cost_usd: float
