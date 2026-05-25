import sys
from pathlib import Path

from rich.console import Console


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_runs import build_aggregate_table, build_metadata_table, format_delta


def _run(prompt_version: str, severity_accuracy: float) -> dict:
    return {
        "run_id": f"run_{prompt_version}",
        "eval_set": "data/eval_sets/incident_eval_v1.jsonl",
        "model": "gpt-4.1-mini",
        "prompt_version": prompt_version,
        "used_openai": False,
        "thresholds": {"passed": True},
        "aggregate": {
            "case_count": 5,
            "severity_accuracy": severity_accuracy,
            "avg_required_tool_recall": 1.0,
        },
    }


def _render(table) -> str:
    console = Console(record=True, width=120)
    console.print(table)
    return console.export_text()


def test_format_delta_for_numeric_values() -> None:
    assert format_delta(0.8, 1.0) == "0.2"


def test_build_metadata_table_includes_prompt_versions() -> None:
    table = build_metadata_table(_run("triage_agent_v1", 1.0), _run("triage_agent_v2", 1.0))
    rendered = _render(table)
    assert "Run Metadata" in rendered
    assert "triage_agent_v1" in rendered
    assert "triage_agent_v2" in rendered


def test_build_aggregate_table_includes_metric_delta() -> None:
    table = build_aggregate_table(_run("triage_agent_v1", 0.8), _run("triage_agent_v2", 1.0))
    rendered = _render(table)
    assert "severity_accuracy" in rendered
    assert "0.2" in rendered
