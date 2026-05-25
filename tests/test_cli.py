import sys

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
    assert "5 cases" in captured.out


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


def test_run_safety_eval_prints_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["incident-safety-eval", "--fail-on-regression"])

    cli.run_safety_eval_main()

    captured = capsys.readouterr()
    assert "Safety Eval" in captured.out
    assert "failed_count" in captured.out
