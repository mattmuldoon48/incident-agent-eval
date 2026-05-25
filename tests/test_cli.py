import sys

from incident_agent_eval import cli


def test_run_eval_validate_only_does_not_run_agent(monkeypatch, capsys) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("run_agent should not be called in validate-only mode")

    monkeypatch.setattr(cli, "run_agent", fail_if_called)
    monkeypatch.setattr(sys, "argv", ["incident-eval", "--validate-only"])

    cli.run_eval_main()

    captured = capsys.readouterr()
    assert "Eval set valid" in captured.out
    assert "5 cases" in captured.out
