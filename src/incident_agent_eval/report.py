from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from incident_agent_eval.schemas import AgentTrace, EvalResult


def print_triage_report(trace: AgentTrace, trace_path: str) -> None:
    console = Console()
    report = trace.final_report
    console.print(Panel.fit(f"[bold]{report.service}[/bold] {report.severity}\n{report.severity_rationale}", title=report.incident_id))
    console.print("[bold]Likely causes[/bold]")
    for item in report.likely_causes:
        console.print(f"- {item}")
    console.print("[bold]Evidence[/bold]")
    for item in report.evidence:
        console.print(f"- [{item.source}] {item.quote_or_summary}")
    console.print("[bold]Recommended next actions[/bold]")
    for item in report.recommended_next_actions:
        console.print(f"- {item}")
    console.print(f"[bold]Escalation[/bold]: {report.escalation_target}")
    console.print(f"[bold]Customer update[/bold]: {report.customer_update_draft}")
    console.print(f"[dim]Trace saved to {trace_path}[/dim]")


def print_eval_table(results: list[EvalResult], aggregate: dict) -> None:
    console = Console()
    table = Table(title="Incident Agent Eval")
    for column in ["case", "sev", "tools", "causes", "evidence", "recs", "violations", "latency_ms", "cost"]:
        table.add_column(column)
    for result in results:
        table.add_row(
            result.eval_case_id,
            str(result.severity_correct),
            f"{result.required_tool_recall:.2f}",
            f"{result.likely_cause_coverage:.2f}",
            f"{result.evidence_coverage:.2f}",
            f"{result.recommendation_coverage:.2f}",
            str(result.forbidden_action_violations),
            str(result.latency_ms),
            f"${result.estimated_cost_usd:.6f}",
        )
    console.print(table)
    console.print(aggregate)
