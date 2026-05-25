from importlib.metadata import entry_points


def test_console_entry_points_are_declared() -> None:
    commands = {
        entry_point.name: entry_point.value
        for entry_point in entry_points(group="console_scripts")
        if entry_point.name.startswith("incident-")
    }

    assert commands["incident-agent"] == "incident_agent_eval.cli:run_agent_main"
    assert commands["incident-eval"] == "incident_agent_eval.cli:run_eval_main"
    assert commands["incident-trace"] == "incident_agent_eval.cli:inspect_trace_main"
    assert commands["incident-compare"] == "incident_agent_eval.cli:compare_runs_main"
