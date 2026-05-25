from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from incident_agent_eval.cli import display_path, run_eval_main, write_csv_report, write_markdown_report


if __name__ == "__main__":
    run_eval_main()
