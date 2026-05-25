from __future__ import annotations

import argparse
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
    return parser.parse_args()


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
        trace, trace_path = run_agent(ROOT / case.incident_file)
        results.append(score_trace(case, trace))
        trace_paths.append(str(trace_path))
        models.add(trace.model)
        used_openai = used_openai or trace.used_openai

    aggregate = aggregate_results(results)
    threshold_result = evaluate_thresholds(aggregate, DEFAULT_THRESHOLDS)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = ROOT / f"reports/eval_runs/{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": timestamp,
        "results": [json.loads(result.model_dump_json()) for result in results],
        "aggregate": aggregate,
        "thresholds": threshold_result,
        "trace_paths": trace_paths,
        "eval_set": str(eval_path),
        "model": ", ".join(sorted(models)),
        "prompt_version": TRIAGE_PROMPT_VERSION,
        "used_openai": used_openai,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_path = output_path.parent / "latest.json"
    latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print_eval_table(results, aggregate)
    if threshold_result["passed"]:
        print("Thresholds passed")
    else:
        print(f"Thresholds failed: {', '.join(threshold_result['failed_metrics'])}")
    print(f"Saved eval report to {output_path}")
    print(f"Updated latest eval report at {latest_path}")
    if args.fail_on_regression and not threshold_result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
