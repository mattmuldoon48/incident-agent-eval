from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_agent_eval.config import get_settings
from incident_agent_eval.security_eval import (
    load_and_validate_security_eval_cases,
    run_security_evaluation,
)


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic prompt-injection and unsafe-tool-use evaluation."
    )
    parser.add_argument("--mode", choices=("baseline", "hardened"), default="baseline")
    parser.add_argument(
        "--dataset",
        default="data/eval_sets/security_eval_v1.json",
        help="Security eval JSON/JSONL path, relative to the project root unless absolute.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/security_eval",
        help="Artifact directory, relative to the project root unless absolute.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the dataset schema and labels without running cases.",
    )
    args = parser.parse_args()

    root = get_settings().project_root
    dataset_path = _resolve(root, args.dataset)
    cases = load_and_validate_security_eval_cases(dataset_path)
    if args.validate_only:
        print(f"Dataset valid: {dataset_path} ({len(cases)} cases)")
        return

    payload, json_path, csv_path = run_security_evaluation(
        cases,
        args.mode,
        _resolve(root, args.output_dir),
    )
    print(json.dumps(payload["aggregate"], indent=2))
    print(f"Detailed JSON: {json_path}")
    print(f"Case CSV: {csv_path}")


if __name__ == "__main__":
    main()
