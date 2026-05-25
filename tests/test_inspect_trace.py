import time
from pathlib import Path

from incident_agent_eval.cli import latest_trace_path, resolve_trace_path


def test_latest_trace_path_returns_newest_json(tmp_path: Path) -> None:
    older = tmp_path / "older.json"
    newer = tmp_path / "newer.json"
    older.write_text("{}", encoding="utf-8")
    time.sleep(0.01)
    newer.write_text("{}", encoding="utf-8")

    assert latest_trace_path(tmp_path) == newer


def test_latest_trace_path_ignores_non_json(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("ignore me", encoding="utf-8")
    trace = tmp_path / "trace.json"
    trace.write_text("{}", encoding="utf-8")

    assert latest_trace_path(tmp_path) == trace


def test_resolve_trace_path_uses_explicit_path() -> None:
    assert resolve_trace_path("reports/traces/example.json", latest=False) == Path("reports/traces/example.json")
