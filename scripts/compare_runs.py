from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/compare_runs.py reports/eval_runs/run_a.json reports/eval_runs/run_b.json")
    left = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["aggregate"]
    right = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["aggregate"]
    table = Table(title="Eval Run Comparison")
    table.add_column("metric")
    table.add_column("run_a")
    table.add_column("run_b")
    table.add_column("delta")
    for metric in sorted(set(left) | set(right)):
        a = left.get(metric, 0)
        b = right.get(metric, 0)
        delta = b - a if isinstance(a, (int, float)) and isinstance(b, (int, float)) else ""
        table.add_row(metric, str(a), str(b), str(delta))
    Console().print(table)


if __name__ == "__main__":
    main()
