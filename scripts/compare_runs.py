from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table


METADATA_FIELDS = ["run_id", "eval_set", "model", "prompt_version", "used_openai"]


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


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/compare_runs.py reports/eval_runs/run_a.json reports/eval_runs/run_b.json")
    left = load_run(sys.argv[1])
    right = load_run(sys.argv[2])
    console = Console()
    console.print(build_metadata_table(left, right))
    console.print(build_aggregate_table(left, right))


if __name__ == "__main__":
    main()
