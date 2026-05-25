from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from incident_agent_eval.agent import run_agent
from incident_agent_eval.report import print_triage_report


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/run_agent.py data/incidents/incident_001.json")
    trace, trace_path = run_agent(sys.argv[1])
    print_triage_report(trace, str(trace_path))


if __name__ == "__main__":
    main()
