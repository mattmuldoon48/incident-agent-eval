from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from incident_agent_eval.config import get_settings
from incident_agent_eval.cost import TokenUsage, estimate_cost_usd
from incident_agent_eval.schemas import TriageReport


def _load_prompt(name: str) -> str:
    path = get_settings().project_root / "prompts" / name
    return path.read_text(encoding="utf-8")


def generate_triage_report(context: dict[str, Any]) -> tuple[TriageReport, TokenUsage, bool]:
    settings = get_settings()
    if not settings.openai_api_key:
        return deterministic_report(context), TokenUsage(), False

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = _load_prompt("triage_agent_v1.txt")
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
    content = response.choices[0].message.content or "{}"
    usage = TokenUsage(
        input_tokens=getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
        output_tokens=getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
    )
    try:
        return TriageReport.model_validate_json(content), usage, True
    except ValidationError:
        report = deterministic_report(context)
        report.safety_notes.append("Model response failed schema validation; deterministic fallback report was used.")
        return report, usage, True


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
            "Review worker concurrency and queue drain rate.",
        ]
    elif service == "auth-service":
        causes = ["bad environment variable", "invalid config rollout"]
        actions = [
            "Page the Identity Platform on-call owner.",
            "Check pod restart logs and recent config diff.",
            "Consider rollback if config validation confirms the rollout is invalid.",
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
