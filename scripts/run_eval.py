from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from incident_agent_eval.agent import run_agent
from incident_agent_eval.evaluators import aggregate_results, score_trace
from incident_agent_eval.report import print_eval_table
from incident_agent_eval.schemas import EvalCase


def main() -> None:
    eval_path = ROOT / "data/eval_sets/incident_eval_v1.jsonl"
    cases = [EvalCase.model_validate_json(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    trace_paths = []
    for case in cases:
        trace, trace_path = run_agent(ROOT / case.incident_file)
        results.append(score_trace(case, trace))
        trace_paths.append(str(trace_path))

    aggregate = aggregate_results(results)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = ROOT / f"reports/eval_runs/{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": timestamp,
        "results": [json.loads(result.model_dump_json()) for result in results],
        "aggregate": aggregate,
        "trace_paths": trace_paths,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print_eval_table(results, aggregate)
    print(f"Saved eval report to {output_path}")


if __name__ == "__main__":
    main()
