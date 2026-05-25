from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/inspect_trace.py reports/traces/some_trace.json")
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
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
    console.print("Likely causes: " + ", ".join(report["likely_causes"]))
    console.print("Next actions: " + " | ".join(report["recommended_next_actions"]))


if __name__ == "__main__":
    main()
