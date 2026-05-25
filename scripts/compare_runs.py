from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from incident_agent_eval.cli import build_aggregate_table, build_metadata_table, compare_runs_main, format_delta, load_run


if __name__ == "__main__":
    compare_runs_main()
