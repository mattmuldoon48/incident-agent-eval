from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from incident_agent_eval.agent import run_agent
from incident_agent_eval.evaluators import DEFAULT_THRESHOLDS, aggregate_results, evaluate_thresholds, score_trace
from incident_agent_eval.llm_client import TRIAGE_PROMPT_VERSION
from incident_agent_eval.report import print_eval_table
from incident_agent_eval.schemas import EvalCase


RESULT_COLUMNS = [
    "eval_case_id",
    "severity_correct",
    "required_tool_recall",
    "likely_cause_coverage",
    "evidence_coverage",
    "recommendation_coverage",
    "forbidden_action_violations",
    "latency_ms",
    "estimated_cost_usd",
]


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def write_csv_report(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for row in payload["results"]:
            writer.writerow({column: row[column] for column in RESULT_COLUMNS})


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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    eval_path = Path(args.eval_set)
    if not eval_path.is_absolute():
        eval_path = ROOT / eval_path
    cases = [EvalCase.model_validate_json(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    trace_paths = []
    models = set()
    used_openai = False
    for case in cases:
        trace, trace_path = run_agent(ROOT / case.incident_file, prompt_version=args.prompt_version)
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
    if threshold_result["passed"]:
        print("Thresholds passed")
    else:
        print(f"Thresholds failed: {', '.join(threshold_result['failed_metrics'])}")
    print(f"Saved eval report to {output_path}")
    print(f"Updated latest eval report at {latest_path}")
    print(f"Saved CSV report to {csv_path}")
    print(f"Saved Markdown report to {markdown_path}")
    if args.fail_on_regression and not threshold_result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
