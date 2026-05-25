from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from incident_agent_eval.config import get_settings
from incident_agent_eval.cost import TokenUsage, estimate_cost_usd
from incident_agent_eval.schemas import TriageReport

TRIAGE_PROMPT_VERSION = "triage_agent_v1"


def prompt_path(prompt_version: str) -> Path:
    return get_settings().project_root / "prompts" / f"{prompt_version}.txt"


def load_prompt(prompt_version: str) -> str:
    path = prompt_path(prompt_version)
    if not path.exists():
        available = ", ".join(path.stem for path in sorted(path.parent.glob("*.txt")))
        raise FileNotFoundError(f"Prompt file not found: {path.name}. Available prompts: {available}")
    return path.read_text(encoding="utf-8")


def prompt_sha256(prompt_version: str) -> str:
    return hashlib.sha256(load_prompt(prompt_version).encode("utf-8")).hexdigest()


def fallback_report(context: dict[str, Any], note: str) -> TriageReport:
    report = deterministic_report(context)
    report.safety_notes.append(note)
    return report


def generate_triage_report(
    context: dict[str, Any],
    prompt_version: str = TRIAGE_PROMPT_VERSION,
    use_openai: bool = True,
) -> tuple[TriageReport, TokenUsage, bool]:
    settings = get_settings()
    prompt = load_prompt(prompt_version)
    if not use_openai or not settings.openai_api_key:
        return deterministic_report(context), TokenUsage(), False

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(context, default=str)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "triage_report",
                    "schema": TriageReport.model_json_schema(),
                    "strict": True,
                },
            },
        )
    except OpenAIError as exc:
        return fallback_report(context, f"OpenAI API call failed; deterministic fallback report was used. Error: {exc.__class__.__name__}"), TokenUsage(), False

    content = response.choices[0].message.content or "{}"
    usage = TokenUsage(
        input_tokens=getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
        output_tokens=getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
    )
    try:
        return TriageReport.model_validate_json(content), usage, True
    except ValidationError:
        return fallback_report(context, "Model response failed schema validation; deterministic fallback report was used."), usage, True


def deterministic_report(context: dict[str, Any]) -> TriageReport:
    incident = context["incident"]
    severity = context["severity"]
    owner = context["owner"]
    service = incident["service"]
    tools_used = context["tools_used"]

    text = json.dumps(context).lower()
    if service == "checkout-api":
        causes = ["recent deployment regression", "database connection timeout"]
        actions = [
            "Page the Checkout Platform on-call owner.",
            "Compare failing requests against the recent deployment version.",
            "Check database connection pool saturation and timeout logs.",
            "Consider rollback if deploy correlation is confirmed and rollback policy is satisfied.",
        ]
    elif service == "payments-worker":
        causes = ["downstream payment provider slowness", "worker concurrency saturation"]
        actions = [
            "Page the Payments Operations owner if backlog continues to grow.",
            "Check provider latency and timeout logs.",
            "Review worker concurrency saturation and queue drain rate.",
        ]
    elif service == "auth-service":
        causes = ["bad environment variable", "invalid config rollout"]
        actions = [
            "Page the Identity Platform on-call owner.",
            "Check pod restart logs and recent config diff.",
            "Consider rollback if config validation confirms the rollout is invalid.",
        ]
    elif service == "search-api":
        causes = ["catalog cache saturation", "upstream catalog slowness"]
        actions = [
            "Page the Search Platform on-call owner if latency remains elevated.",
            "Check catalog cache saturation metrics and cache client logs.",
            "Review query enrichment changes from the recent search-api deploy.",
        ]
    elif service == "reporting-api":
        causes = ["analytics exporter lag", "internal reporting freshness delay"]
        actions = [
            "Notify the Analytics Platform owner during business hours.",
            "Monitor exporter lag and scheduled report completion metrics.",
            "Review analytics exporter logs for delayed dashboard freshness updates.",
        ]
    elif service == "inventory-api":
        causes = ["database read replica saturation", "slow query plan regression"]
        actions = [
            "Page the Inventory Platform owner if latency remains elevated.",
            "Check database latency, read replica saturation, and slow query logs.",
            "Review query plans without changing database configuration from this agent.",
        ]
    elif service == "billing-api":
        causes = ["IAM policy regression", "billing writer role permission denial"]
        actions = [
            "Page the Billing Platform owner and IAM reviewer.",
            "Compare the recent IAM policy change with the prior working policy.",
            "Prepare a permission fix or rollback for human approval if AccessDenied correlation is confirmed.",
        ]
    elif service == "notifications-api":
        causes = ["synthetic canary false positive", "alert threshold too sensitive"]
        actions = [
            "Notify the Notifications Platform owner during normal triage.",
            "Verify customer-facing notification metrics remain within baseline.",
            "Review alert threshold tuning after confirming the alert is noisy.",
        ]
    elif service == "media-api":
        causes = ["partial regional dependency degradation", "us-east-1 upload timeout increase"]
        actions = [
            "Page the Media Platform owner for regional customer impact.",
            "Compare us-east-1 upload failures against healthy regions.",
            "Consider approved traffic steering only through a human operations process.",
        ]
    elif service == "log-ingestor":
        causes = ["logging pipeline backpressure", "indexer throttling"]
        actions = [
            "Page the Observability Platform owner if delayed logs impair incident response.",
            "Check log ingestion lag and indexer throttle metrics.",
            "Preserve observability data; do not delete logs or disable alerts.",
        ]
    else:
        causes = ["unknown service degradation"]
        actions = ["Page the owning service team.", "Review metrics, logs, deploys, and relevant runbooks."]

    evidence = []
    for metric in context.get("metrics", [])[:2]:
        evidence.append(
            {
                "source": "metrics.jsonl",
                "quote_or_summary": f"{metric['service']} {metric['metric']}={metric['value']} at {metric['timestamp']}",
                "relevance": "Shows current service health during the incident window.",
            }
        )
    for deploy in context.get("deploys", [])[:1]:
        evidence.append(
            {
                "source": "deploys.jsonl",
                "quote_or_summary": f"Deploy {deploy['version']} completed at {deploy['timestamp']}: {deploy['summary']}",
                "relevance": "Recent change may correlate with symptom onset.",
            }
        )
    for log in context.get("logs", [])[:2]:
        evidence.append(
            {
                "source": "logs.jsonl",
                "quote_or_summary": log["message"],
                "relevance": "Log line matches reported symptoms or likely cause.",
            }
        )
    for runbook in context.get("runbooks", [])[:1]:
        evidence.append(
            {
                "source": str(runbook["source"]),
                "quote_or_summary": str(runbook["snippet"])[:220],
                "relevance": "Runbook guidance grounds the triage recommendations.",
            }
        )

    if "rollback now" in text:
        actions.append("Do not execute rollback from this agent; escalate for human approval.")

    return TriageReport(
        incident_id=incident["id"],
        service=service,
        severity=severity["severity"],
        severity_rationale=severity["explanation"],
        likely_causes=causes,
        evidence=evidence,
        recommended_next_actions=actions,
        escalation_target=f"{owner.get('team', 'unknown')} via {owner.get('escalation', 'unknown')}",
        customer_update_draft=(
            f"We are investigating degraded behavior in {service}. Current triage points to {', '.join(causes)}. "
            "The team is reviewing metrics, logs, recent changes, and runbook guidance."
        ),
        safety_notes=[
            "This agent is read-only and did not mutate infrastructure.",
            "Rollback, restart, scaling, or config changes require human approval outside this tool.",
        ],
        tools_used=tools_used,
    )


def estimate_report_cost(model: str, usage: TokenUsage) -> float:
    return estimate_cost_usd(model, usage)
