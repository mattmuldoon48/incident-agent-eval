from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from incident_agent_eval.agent import run_agent
from incident_agent_eval.config import get_settings
from incident_agent_eval.eval_sets import load_and_validate_eval_cases
from incident_agent_eval.evaluators import DEFAULT_THRESHOLDS, aggregate_results, evaluate_thresholds, score_trace
from incident_agent_eval.llm_client import TRIAGE_PROMPT_VERSION
from incident_agent_eval.report import print_eval_table, print_triage_report
from incident_agent_eval.safety_eval import (
    aggregate_safety_eval_results,
    load_safety_eval_cases,
    score_safety_eval_case,
)
from incident_agent_eval.schemas import EvalCase, SafetyEvalResult

ROOT = get_settings().project_root

RESULT_COLUMNS = [
    "eval_case_id",
    "severity_correct",
    "required_tool_recall",
    "likely_cause_coverage",
    "evidence_coverage",
    "recommendation_coverage",
    "forbidden_action_violations",
    "missing_required_tools",
    "missed_likely_causes",
    "missed_evidence",
    "missed_recommendations",
    "forbidden_action_matches",
    "latency_ms",
    "estimated_cost_usd",
]

METADATA_FIELDS = ["run_id", "eval_set", "model", "prompt_version", "used_openai"]

REQUIRED_DOCTOR_PATHS = [
    "data/incidents",
    "data/mock_observability/metrics.jsonl",
    "data/mock_observability/logs.jsonl",
    "data/mock_observability/deploys.jsonl",
    "data/mock_observability/service_owners.json",
    "data/runbooks",
    "data/eval_sets/incident_eval_v1.jsonl",
    "prompts/triage_agent_v1.txt",
    "prompts/safety_policy.txt",
]

OPTIONAL_DOCTOR_OUTPUT_PATHS = ["reports/traces", "reports/eval_runs"]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_csv_report(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for row in payload["results"]:
            writer.writerow({column: _csv_value(row.get(column, [])) for column in RESULT_COLUMNS})


def _csv_value(value: Any) -> str | int | float:
    if isinstance(value, list | dict):
        return json.dumps(value)
    return value


def write_markdown_report(path: Path, payload: dict) -> None:
    aggregate = payload["aggregate"]
    thresholds = payload["thresholds"]
    lines = [
        f"# Incident Agent Eval Run {payload['run_id']}",
        "",
        f"- Eval set: `{payload['eval_set']}`",
        f"- Model: `{payload['model']}`",
        f"- Prompt version: `{payload['prompt_version']}`",
        f"- Used OpenAI: `{payload['used_openai']}`",
        f"- Thresholds passed: `{thresholds['passed']}`",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for metric, value in aggregate.items():
        lines.append(f"| {metric} | {value} |")
    lines.extend(
        [
            "",
            "## Case Metrics",
            "",
            "| Case | Severity | Tools | Causes | Evidence | Recommendations | Violations | Latency ms | Cost |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["results"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['eval_case_id']}`",
                    str(row["severity_correct"]),
                    f"{row['required_tool_recall']:.2f}",
                    f"{row['likely_cause_coverage']:.2f}",
                    f"{row['evidence_coverage']:.2f}",
                    f"{row['recommendation_coverage']:.2f}",
                    str(row["forbidden_action_violations"]),
                    str(row["latency_ms"]),
                    f"{row['estimated_cost_usd']:.6f}",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Case Diagnostics", ""])
    for row in payload["results"]:
        lines.extend(
            [
                f"### `{row['eval_case_id']}`",
                "",
                f"- Missing tools: `{', '.join(row['missing_required_tools']) or 'none'}`",
                f"- Missed likely causes: `{', '.join(row['missed_likely_causes']) or 'none'}`",
                f"- Missed evidence: `{', '.join(row['missed_evidence']) or 'none'}`",
                f"- Missed recommendations: `{', '.join(row['missed_recommendations']) or 'none'}`",
                f"- Forbidden matches: `{', '.join(row['forbidden_action_matches']) or 'none'}`",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def filter_cases(cases: list[EvalCase], case_ids: list[str] | None) -> list[EvalCase]:
    if not case_ids:
        return cases
    requested = set(case_ids)
    available = {case.id for case in cases}
    missing = sorted(requested - available)
    if missing:
        raise ValueError(f"Unknown eval case id(s): {', '.join(missing)}")
    return [case for case in cases if case.id in requested]


def print_case_list(cases: list[EvalCase]) -> None:
    table = Table(title="Eval Cases")
    table.add_column("case")
    table.add_column("incident")
    table.add_column("expected severity")
    table.add_column("required tools")
    for case in cases:
        table.add_row(
            case.id,
            case.incident_file,
            case.expected_severity,
            str(len(case.required_tools)),
        )
    Console().print(table)


def build_doctor_checks(root: Path, openai_api_key: str | None, openai_model: str) -> list[dict[str, str | bool]]:
    checks: list[dict[str, str | bool]] = []
    for relative_path in REQUIRED_DOCTOR_PATHS:
        path = root / relative_path
        checks.append(
            {
                "check": relative_path,
                "required": True,
                "ok": path.exists(),
                "detail": "found" if path.exists() else "missing",
            }
        )
    for relative_path in OPTIONAL_DOCTOR_OUTPUT_PATHS:
        path = root / relative_path
        checks.append(
            {
                "check": relative_path,
                "required": False,
                "ok": path.exists(),
                "detail": "found" if path.exists() else "will be created by agent/eval runs",
            }
        )
    checks.append(
        {
            "check": "OPENAI_MODEL",
            "required": True,
            "ok": bool(openai_model),
            "detail": openai_model or "missing",
        }
    )
    checks.append(
        {
            "check": "OPENAI_API_KEY",
            "required": False,
            "ok": bool(openai_api_key),
            "detail": "set" if openai_api_key else "not set; deterministic fallback is available",
        }
    )
    return checks


def print_doctor_checks(checks: list[dict[str, str | bool]]) -> None:
    table = Table(title="Incident Agent Eval Doctor")
    table.add_column("check")
    table.add_column("required")
    table.add_column("status")
    table.add_column("detail")
    for check in checks:
        ok = bool(check["ok"])
        status = "ok" if ok else "missing"
        table.add_row(str(check["check"]), str(check["required"]), status, str(check["detail"]))
    Console().print(table)


def doctor_main() -> None:
    settings = get_settings()
    checks = build_doctor_checks(settings.project_root, settings.openai_api_key, settings.openai_model)
    print_doctor_checks(checks)
    required_failures = [check for check in checks if check["required"] and not check["ok"]]
    if required_failures:
        raise SystemExit(1)


def run_agent_main() -> None:
    parser = argparse.ArgumentParser(description="Run incident triage for one incident JSON file.")
    parser.add_argument("incident_file", help="Path to incident JSON file.")
    parser.add_argument(
        "--prompt-version",
        default=TRIAGE_PROMPT_VERSION,
        help="Prompt file stem from prompts/, for example triage_agent_v1.",
    )
    parser.add_argument(
        "--no-openai",
        action="store_true",
        help="Force deterministic fallback generation even when OPENAI_API_KEY is set.",
    )
    args = parser.parse_args()
    trace, trace_path = run_agent(args.incident_file, prompt_version=args.prompt_version, use_openai=not args.no_openai)
    print_triage_report(trace, str(trace_path))


def run_eval_main() -> None:
    parser = argparse.ArgumentParser(description="Run incident-agent eval cases.")
    parser.add_argument(
        "--eval-set",
        default="data/eval_sets/incident_eval_v1.jsonl",
        help="Path to eval JSONL file, relative to project root unless absolute.",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit nonzero if aggregate metrics miss the configured quality thresholds.",
    )
    parser.add_argument(
        "--prompt-version",
        default=TRIAGE_PROMPT_VERSION,
        help="Prompt file stem from prompts/, for example triage_agent_v1.",
    )
    parser.add_argument(
        "--no-openai",
        action="store_true",
        help="Force deterministic fallback generation even when OPENAI_API_KEY is set.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the eval set and exit without running the agent.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        help="Run only the specified eval case id. Can be passed more than once.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List eval cases and exit without running the agent.",
    )
    args = parser.parse_args()

    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = ROOT / eval_path
    cases = filter_cases(load_and_validate_eval_cases(eval_path, ROOT), args.case_id)
    if args.list_cases:
        print_case_list(cases)
        return
    if args.validate_only:
        print(f"Eval set valid: {display_path(eval_path)} ({len(cases)} cases)")
        return

    results = []
    trace_paths = []
    models = set()
    used_openai = False
    for case in cases:
        trace, trace_path = run_agent(ROOT / case.incident_file, prompt_version=args.prompt_version, use_openai=not args.no_openai)
        results.append(score_trace(case, trace))
        trace_paths.append(str(trace_path))
        models.add(trace.model)
        used_openai = used_openai or trace.used_openai

    aggregate = aggregate_results(results)
    threshold_result = evaluate_thresholds(aggregate, DEFAULT_THRESHOLDS)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = ROOT / f"reports/eval_runs/{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": timestamp,
        "results": [json.loads(result.model_dump_json()) for result in results],
        "aggregate": aggregate,
        "thresholds": threshold_result,
        "trace_paths": trace_paths,
        "eval_set": display_path(eval_path),
        "case_ids": [case.id for case in cases],
        "model": ", ".join(sorted(models)),
        "prompt_version": args.prompt_version,
        "used_openai": used_openai,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_path = output_path.parent / "latest.json"
    latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    csv_path = output_path.with_suffix(".csv")
    markdown_path = output_path.with_suffix(".md")
    write_csv_report(csv_path, payload)
    write_markdown_report(markdown_path, payload)
    write_csv_report(output_path.parent / "latest.csv", payload)
    write_markdown_report(output_path.parent / "latest.md", payload)

    print_eval_table(results, aggregate)
    print("Thresholds passed" if threshold_result["passed"] else f"Thresholds failed: {', '.join(threshold_result['failed_metrics'])}")
    print(f"Saved eval report to {output_path}")
    print(f"Updated latest eval report at {latest_path}")
    print(f"Saved CSV report to {csv_path}")
    print(f"Saved Markdown report to {markdown_path}")
    if args.fail_on_regression and not threshold_result["passed"]:
        raise SystemExit(1)


def print_safety_eval_table(results: list[SafetyEvalResult], aggregate: dict[str, int | float]) -> None:
    table = Table(title="Safety Eval")
    table.add_column("case")
    table.add_column("passed")
    table.add_column("expected safe")
    table.add_column("actual safe")
    table.add_column("missed")
    table.add_column("unexpected")
    for result in results:
        table.add_row(
            result.eval_case_id,
            str(result.passed),
            str(result.expected_safe),
            str(result.actual_safe),
            ", ".join(result.missed_violations) or "none",
            ", ".join(result.unexpected_violations) or "none",
        )
    console = Console()
    console.print(table)
    console.print(aggregate)


def run_safety_eval_main() -> None:
    parser = argparse.ArgumentParser(description="Run direct safety guardrail eval cases.")
    parser.add_argument(
        "--eval-set",
        default="data/eval_sets/safety_eval_v1.jsonl",
        help="Path to safety eval JSONL file, relative to project root unless absolute.",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit nonzero if any safety eval case fails.",
    )
    args = parser.parse_args()

    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = ROOT / eval_path
    cases = load_safety_eval_cases(eval_path)
    results = [score_safety_eval_case(case) for case in cases]
    aggregate = aggregate_safety_eval_results(results)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = ROOT / f"reports/eval_runs/safety_{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": f"safety_{timestamp}",
        "eval_set": display_path(eval_path),
        "results": [json.loads(result.model_dump_json()) for result in results],
        "aggregate": aggregate,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_path = output_path.parent / "latest_safety.json"
    latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print_safety_eval_table(results, aggregate)
    print(f"Saved safety eval report to {output_path}")
    print(f"Updated latest safety eval report at {latest_path}")
    if args.fail_on_regression and aggregate["failed_count"] > 0:
        raise SystemExit(1)


def latest_trace_path(trace_dir: Path | None = None) -> Path:
    directory = trace_dir or ROOT / "reports/traces"
    traces = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not traces:
        raise FileNotFoundError(f"No trace JSON files found in {directory}")
    return traces[0]


def resolve_trace_path(trace_file: str | None, latest: bool) -> Path:
    if latest:
        return latest_trace_path()
    if not trace_file:
        raise SystemExit("Usage: incident-trace reports/traces/some_trace.json OR incident-trace --latest")
    return Path(trace_file)


def print_trace(payload: dict) -> None:
    console = Console()
    table = Table(title=f"Trace {payload['trace_id']}")
    table.add_column("tool")
    table.add_column("success")
    table.add_column("summary")
    for call in payload["tool_calls"]:
        table.add_row(call["tool_name"], str(call["success"]), call["result_summary"])
    console.print(table)
    report = payload["final_report"]
    console.print(f"[bold]{report['service']}[/bold] {report['severity']}: {report['severity_rationale']}")
    console.print(
        f"Schema: {payload.get('schema_version', 'unknown')} | Model: {payload['model']} | "
        f"Prompt: {payload.get('prompt_version', 'unknown')} "
        f"({payload.get('prompt_sha256', 'unknown')[:12]}) | OpenAI: {payload.get('used_openai', 'unknown')}"
    )
    safety = payload.get("safety_check", {})
    console.print(f"Safety: {safety.get('safe', 'unknown')} violations={safety.get('violations', [])}")
    console.print("Likely causes: " + ", ".join(report["likely_causes"]))
    console.print("Next actions: " + " | ".join(report["recommended_next_actions"]))


def inspect_trace_main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a saved incident-agent trace.")
    parser.add_argument("trace_file", nargs="?", help="Path to trace JSON file.")
    parser.add_argument("--latest", action="store_true", help="Inspect the newest trace in reports/traces/.")
    args = parser.parse_args()
    path = resolve_trace_path(args.trace_file, args.latest)
    payload = json.loads(path.read_text(encoding="utf-8"))
    print_trace(payload)


def load_run(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def format_delta(left: Any, right: Any) -> str:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return str(round(right - left, 6))
    return ""


def build_metadata_table(left: dict[str, Any], right: dict[str, Any]) -> Table:
    table = Table(title="Run Metadata")
    table.add_column("field")
    table.add_column("run_a")
    table.add_column("run_b")
    for field in METADATA_FIELDS:
        table.add_row(field, str(left.get(field, "")), str(right.get(field, "")))
    table.add_row(
        "thresholds_passed",
        str(left.get("thresholds", {}).get("passed", "")),
        str(right.get("thresholds", {}).get("passed", "")),
    )
    return table


def build_aggregate_table(left: dict[str, Any], right: dict[str, Any]) -> Table:
    left_aggregate = left["aggregate"]
    right_aggregate = right["aggregate"]
    table = Table(title="Eval Run Comparison")
    table.add_column("metric")
    table.add_column("run_a")
    table.add_column("run_b")
    table.add_column("delta")
    for metric in sorted(set(left_aggregate) | set(right_aggregate)):
        a = left_aggregate.get(metric, 0)
        b = right_aggregate.get(metric, 0)
        table.add_row(metric, str(a), str(b), format_delta(a, b))
    return table


def compare_runs_main() -> None:
    parser = argparse.ArgumentParser(description="Compare two incident-agent eval reports.")
    parser.add_argument("run_a", help="Path to first eval JSON report.")
    parser.add_argument("run_b", help="Path to second eval JSON report.")
    args = parser.parse_args()
    left = load_run(args.run_a)
    right = load_run(args.run_b)
    console = Console()
    console.print(build_metadata_table(left, right))
    console.print(build_aggregate_table(left, right))
