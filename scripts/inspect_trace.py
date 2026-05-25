from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from incident_agent_eval.cli import inspect_trace_main, latest_trace_path, print_trace, resolve_trace_path


if __name__ == "__main__":
    inspect_trace_main()
