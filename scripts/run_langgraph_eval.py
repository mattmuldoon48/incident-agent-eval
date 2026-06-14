from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from incident_agent_eval.cli import (
    ROOT,
    display_path,
    filter_cases,
    print_case_list,
    write_csv_report,
    write_markdown_report,
)
from incident_agent_eval.eval_sets import load_and_validate_eval_cases
from incident_agent_eval.evaluators import DEFAULT_THRESHOLDS, aggregate_results, evaluate_thresholds, score_trace
from incident_agent_eval.langgraph_runner import LANGGRAPH_ORCHESTRATION_MODE, run_langgraph_agent
from incident_agent_eval.llm_client import TRIAGE_PROMPT_VERSION
from incident_agent_eval.report import print_eval_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Run incident-agent eval cases through LangGraph orchestration.")
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
        trace, trace_path = run_langgraph_agent(
            ROOT / case.incident_file,
            prompt_version=args.prompt_version,
            use_openai=not args.no_openai,
        )
        results.append(score_trace(case, trace))
        trace_paths.append(str(trace_path))
        models.add(trace.model)
        used_openai = used_openai or trace.used_openai

    aggregate = aggregate_results(results)
    threshold_result = evaluate_thresholds(aggregate, DEFAULT_THRESHOLDS)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = ROOT / f"reports/eval_runs/langgraph_{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": f"langgraph_{timestamp}",
        "orchestration_mode": LANGGRAPH_ORCHESTRATION_MODE,
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
    latest_path = output_path.parent / "latest_langgraph.json"
    latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    csv_path = output_path.with_suffix(".csv")
    markdown_path = output_path.with_suffix(".md")
    write_csv_report(csv_path, payload)
    write_markdown_report(markdown_path, payload)
    write_csv_report(output_path.parent / "latest_langgraph.csv", payload)
    write_markdown_report(output_path.parent / "latest_langgraph.md", payload)

    print_eval_table(results, aggregate)
    print(
        "Thresholds passed"
        if threshold_result["passed"]
        else f"Thresholds failed: {', '.join(threshold_result['failed_metrics'])}"
    )
    print(f"Saved LangGraph eval report to {output_path}")
    print(f"Updated latest LangGraph eval report at {latest_path}")
    print(f"Saved CSV report to {csv_path}")
    print(f"Saved Markdown report to {markdown_path}")
    if args.fail_on_regression and not threshold_result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
