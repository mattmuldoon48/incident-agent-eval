import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_eval import display_path, write_csv_report, write_markdown_report


def _payload() -> dict:
    return {
        "run_id": "test_run",
        "results": [
            {
                "eval_case_id": "eval_test",
                "severity_correct": 1,
                "required_tool_recall": 1.0,
                "likely_cause_coverage": 0.5,
                "evidence_coverage": 0.75,
                "recommendation_coverage": 1.0,
                "forbidden_action_violations": 0,
                "latency_ms": 123,
                "estimated_cost_usd": 0.001,
            }
        ],
        "aggregate": {
            "case_count": 1,
            "severity_accuracy": 1.0,
            "avg_required_tool_recall": 1.0,
            "avg_recommendation_coverage": 1.0,
            "avg_likely_cause_coverage": 0.5,
            "avg_evidence_coverage": 0.75,
            "total_forbidden_action_violations": 0,
            "avg_latency_ms": 123.0,
            "total_estimated_cost_usd": 0.001,
        },
        "thresholds": {"passed": True},
        "eval_set": "data/eval_sets/incident_eval_v1.jsonl",
        "model": "gpt-4.1-mini",
        "prompt_version": "triage_agent_v1",
        "used_openai": False,
    }


def test_write_csv_report(tmp_path: Path) -> None:
    path = tmp_path / "eval.csv"
    write_csv_report(path, _payload())

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["eval_case_id"] == "eval_test"
    assert rows[0]["evidence_coverage"] == "0.75"


def test_write_markdown_report(tmp_path: Path) -> None:
    path = tmp_path / "eval.md"
    write_markdown_report(path, _payload())

    text = path.read_text(encoding="utf-8")
    assert "# Incident Agent Eval Run test_run" in text
    assert "| eval_test |" not in text
    assert "`eval_test`" in text
    assert "avg_evidence_coverage" in text


def test_display_path_uses_relative_project_paths() -> None:
    assert display_path(ROOT / "data/eval_sets/incident_eval_v1.jsonl") == "data/eval_sets/incident_eval_v1.jsonl"
