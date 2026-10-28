import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from incident_agent_eval import cli
from incident_agent_eval.eval_sets import load_and_validate_eval_cases


def test_run_eval_validate_only_does_not_run_agent(monkeypatch, capsys) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("run_agent should not be called in validate-only mode")

    monkeypatch.setattr(cli, "run_agent", fail_if_called)
    monkeypatch.setattr(sys, "argv", ["incident-eval", "--validate-only"])

    cli.run_eval_main()

    captured = capsys.readouterr()
    assert "Eval set valid" in captured.out
    assert "10 cases" in captured.out


def test_run_eval_list_cases_does_not_run_agent(monkeypatch, capsys) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("run_agent should not be called in list-cases mode")

    monkeypatch.setattr(cli, "run_agent", fail_if_called)
    monkeypatch.setattr(sys, "argv", ["incident-eval", "--list-cases"])

    cli.run_eval_main()

    captured = capsys.readouterr()
    assert "Eval Cases" in captured.out
    assert "eval_001" in captured.out
    assert "SEV-2" in captured.out


def test_filter_cases_selects_requested_ids() -> None:
    cases = load_and_validate_eval_cases(cli.ROOT / "data/eval_sets/incident_eval_v1.jsonl", cli.ROOT)

    filtered = cli.filter_cases(cases, ["eval_001", "eval_003"])

    assert [case.id for case in filtered] == ["eval_001", "eval_003"]


def test_filter_cases_rejects_unknown_id() -> None:
    cases = load_and_validate_eval_cases(cli.ROOT / "data/eval_sets/incident_eval_v1.jsonl", cli.ROOT)

    try:
        cli.filter_cases(cases, ["eval_missing"])
    except ValueError as exc:
        assert "eval_missing" in str(exc)
    else:
        raise AssertionError("Expected unknown eval case id to raise")


def test_build_doctor_checks_marks_required_paths() -> None:
    checks = cli.build_doctor_checks(cli.ROOT, openai_api_key=None, openai_model="gpt-4.1-mini")

    by_name = {str(check["check"]): check for check in checks}

    assert by_name["data/incidents"]["ok"]
    assert by_name["data/incidents"]["required"]
    assert by_name["OPENAI_MODEL"]["ok"]
    assert not by_name["OPENAI_API_KEY"]["required"]
    assert "fallback" in str(by_name["OPENAI_API_KEY"]["detail"])


def test_build_doctor_checks_detects_missing_required_path(tmp_path) -> None:
    checks = cli.build_doctor_checks(tmp_path, openai_api_key="secret", openai_model="gpt-4.1-mini")

    by_name = {str(check["check"]): check for check in checks}

    assert not by_name["data/incidents"]["ok"]
    assert by_name["data/incidents"]["required"]


@pytest.mark.parametrize("contents", ["", " \n\t\n"])
def test_run_safety_eval_rejects_empty_input_without_replacing_reports(
    tmp_path, monkeypatch, contents
) -> None:
    valid_eval_set = cli.ROOT / "data/eval_sets/safety_eval_v1.jsonl"
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["incident-safety-eval", "--eval-set", str(valid_eval_set), "--fail-on-regression"],
    )
    cli.run_safety_eval_main()
    report_dir = tmp_path / "reports/eval_runs"
    original_files = {path.name: path.read_bytes() for path in report_dir.iterdir()}
    aggregate = json.loads(original_files["latest_safety.json"])["aggregate"]
    assert aggregate["case_count"] == 8
    assert aggregate["failed_count"] == 0

    empty_eval_set = tmp_path / "empty.jsonl"
    empty_eval_set.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv",
        ["incident-safety-eval", "--eval-set", str(empty_eval_set), "--fail-on-regression"],
    )
    with pytest.raises(ValueError):
        cli.run_safety_eval_main()

    assert {path.name: path.read_bytes() for path in report_dir.iterdir()} == original_files


@pytest.mark.skipif(shutil.which("make") is None, reason="Make targets require make")
def test_make_targets_preserve_paths_with_spaces(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    root = tmp_path / "project with spaces"
    for directory in ("data", "prompts"):
        shutil.copytree(repo / directory, root / directory)
    incident_path = root / "incident with spaces.json"
    incident = json.loads((repo / "data/incidents/incident_001.json").read_text(encoding="utf-8"))
    incident["id"] = "incident_spaced_path"
    incident_path.write_text(json.dumps(incident), encoding="utf-8")
    env = {
        **os.environ,
        "PROJECT_ROOT": str(root),
        "OPENAI_API_KEY": "",
        "PYTHONPATH": str(repo / "src"),
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
        "COLUMNS": "200",
    }

    def run_make(target: str, *assignments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["make", "--silent", "--no-print-directory", target, f"PYTHON={Path(sys.executable).name}", *assignments],
            cwd=repo, env=env, check=True, capture_output=True, text=True,
        )

    run_make("agent", f"INCIDENT={incident_path}")
    trace_path, = (root / "reports/traces").glob("*.json")
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["incident_id"] == "incident_spaced_path"
    assert trace["used_openai"] is False

    inspected = run_make("trace", f"TRACE={trace_path}")
    assert trace["trace_id"] in inspected.stdout

    baseline = root / "baseline run.json"
    candidate = root / "candidate run.json"
    baseline.write_text(
        json.dumps({"run_id": "spaced-baseline", "aggregate": {"severity_accuracy": 0.2}}),
        encoding="utf-8",
    )
    candidate.write_text(
        json.dumps({"run_id": "spaced-candidate", "aggregate": {"severity_accuracy": 0.9}}),
        encoding="utf-8",
    )
    compared = run_make("compare", f"RUN_A={baseline}", f"RUN_B={candidate}")
    assert "spaced-baseline" in compared.stdout
    assert "spaced-candidate" in compared.stdout
    assert "0.7" in compared.stdout
