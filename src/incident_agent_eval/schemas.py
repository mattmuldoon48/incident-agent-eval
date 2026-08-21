from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TRACE_SCHEMA_VERSION = "1.0"
INCIDENT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
IncidentIdentifier = Annotated[
    str,
    Field(min_length=1, pattern=INCIDENT_ID_PATTERN),
]



class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IncidentInput(StrictBaseModel):
    id: IncidentIdentifier
    service: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    symptoms: list[str] = Field(min_length=1)
    started_at: datetime

    @field_validator("service", "summary")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str, info) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        return value

    @field_validator("symptoms")
    @classmethod
    def symptom_entries_must_not_be_blank(cls, value: list[str]) -> list[str]:
        if any(not symptom.strip() for symptom in value):
            raise ValueError("symptoms entries must not be blank")
        return value


class ToolCall(StrictBaseModel):
    tool_name: str
    args: dict[str, Any]
    result_summary: str
    started_at: datetime
    completed_at: datetime
    success: bool
    error: str | None = None

    @model_validator(mode="after")
    def completion_must_not_precede_start(self) -> "ToolCall":
        if self.completed_at < self.started_at:
            raise ValueError("Tool call completed_at must not precede started_at")
        return self


class EvidenceItem(StrictBaseModel):
    source: str
    quote_or_summary: str
    relevance: str


class TriageReport(StrictBaseModel):
    incident_id: IncidentIdentifier
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
    schema_version: str = TRACE_SCHEMA_VERSION
    orchestration_mode: str = "deterministic"
    trace_id: str
    incident_id: IncidentIdentifier
    started_at: datetime
    completed_at: datetime
    model: str
    prompt_version: str
    prompt_sha256: str
    used_openai: bool
    tool_calls: list[ToolCall]
    final_report: TriageReport
    safety_check: SafetyCheck
    estimated_cost_usd: float
    latency_ms: int

    @model_validator(mode="after")
    def completion_must_not_precede_start(self) -> "AgentTrace":
        if self.completed_at < self.started_at:
            raise ValueError("Trace completed_at must not precede started_at")
        return self


class EvalCase(StrictBaseModel):
    id: str
    incident_file: str
    expected_severity: str
    required_tools: list[str]
    expected_likely_causes: list[str]
    required_recommendations: list[str]
    required_evidence: list[str] = Field(default_factory=list)
    forbidden_actions: list[str]


class EvalResult(StrictBaseModel):
    eval_case_id: str
    severity_correct: int = Field(..., ge=0, le=1)
    required_tool_recall: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    recommendation_coverage: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    likely_cause_coverage: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    evidence_coverage: float = Field(..., ge=0, le=1, allow_inf_nan=False)
    forbidden_action_violations: int = Field(..., ge=0)
    missing_required_tools: list[str] = Field(default_factory=list)
    matched_likely_causes: list[str] = Field(default_factory=list)
    missed_likely_causes: list[str] = Field(default_factory=list)
    matched_recommendations: list[str] = Field(default_factory=list)
    missed_recommendations: list[str] = Field(default_factory=list)
    matched_evidence: list[str] = Field(default_factory=list)
    missed_evidence: list[str] = Field(default_factory=list)
    forbidden_action_matches: list[str] = Field(default_factory=list)
    latency_ms: int = Field(..., ge=0)
    estimated_cost_usd: float = Field(..., ge=0, allow_inf_nan=False)


class SafetyEvalCase(StrictBaseModel):
    id: str
    report: dict[str, Any]
    expected_safe: bool
    expected_violations: list[str] = Field(default_factory=list)


class SafetyEvalResult(StrictBaseModel):
    eval_case_id: str
    passed: bool
    expected_safe: bool
    actual_safe: bool
    expected_violations: list[str]
    actual_violations: list[str]
    missed_violations: list[str]
    unexpected_violations: list[str]


class SecurityEvidence(StrictBaseModel):
    id: str
    source: Literal["metrics", "logs", "deploys", "runbook", "owner", "incident_note"]
    content: str
    trusted: bool = True

    @field_validator("id", "content")
    def evidence_fields_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Security evidence fields must not be blank")
        return value


class SecurityIncident(StrictBaseModel):
    service: str
    summary: str
    symptoms: list[str]


class SecurityEvalCase(StrictBaseModel):
    id: str
    case_type: Literal["normal", "adversarial"]
    title: str
    incident: SecurityIncident
    evidence: list[SecurityEvidence]
    expected_severity: str = Field(pattern=r"^SEV-[1-4]$")
    allowed_tools: list[str]
    forbidden_tools: list[str]
    expected_tools: list[str]
    expected_root_cause_category: str
    contains_injection: bool
    should_refuse: bool
    expected_safe_behavior: str
    rationale: str


class SecurityAgentOutput(StrictBaseModel):
    mode: Literal["baseline", "hardened"]
    severity: str = Field(pattern=r"^SEV-[1-4]$")
    root_cause_category: str
    tool_calls: list[str]
    refused_actions: list[str]
    completed_analysis: bool
    analysis_summary: str
    cited_evidence_ids: list[str]
    followed_injection: bool


class SecurityCaseResult(StrictBaseModel):
    case: SecurityEvalCase
    output: SecurityAgentOutput
    attack_succeeded: int
    forbidden_tool_called: int
    correct_tool_selection: int
    severity_correct: int
    root_cause_correct: int
    refusal_correct: int
    false_refusal: int
    normal_task_completed: int
    evidence_grounding: float
    forbidden_tool_calls: list[str]
    missing_expected_tools: list[str]
    unexpected_tool_calls: list[str]
    ungrounded_evidence_ids: list[str]
