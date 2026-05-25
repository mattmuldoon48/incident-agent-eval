from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a saved incident-agent trace.")
    parser.add_argument("trace_file", nargs="?", help="Path to trace JSON file.")
    parser.add_argument("--latest", action="store_true", help="Inspect the newest trace in reports/traces/.")
    return parser.parse_args()


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
        raise SystemExit("Usage: python scripts/inspect_trace.py reports/traces/some_trace.json OR python scripts/inspect_trace.py --latest")
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
    console.print(f"Model: {payload['model']} | Prompt: {payload.get('prompt_version', 'unknown')} | OpenAI: {payload.get('used_openai', 'unknown')}")
    safety = payload.get("safety_check", {})
    console.print(f"Safety: {safety.get('safe', 'unknown')} violations={safety.get('violations', [])}")
    console.print("Likely causes: " + ", ".join(report["likely_causes"]))
    console.print("Next actions: " + " | ".join(report["recommended_next_actions"]))


def main() -> None:
    args = parse_args()
    path = resolve_trace_path(args.trace_file, args.latest)
    payload = json.loads(path.read_text(encoding="utf-8"))
    print_trace(payload)


if __name__ == "__main__":
    main()
