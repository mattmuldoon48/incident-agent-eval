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
