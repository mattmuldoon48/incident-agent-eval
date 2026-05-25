from incident_agent_eval.safety import find_forbidden_actions, validate_final_report


def test_safety_checker_catches_destructive_actions() -> None:
    report = {"recommended_next_actions": ["restart the pods now", "delete the failing pods"]}
    result = validate_final_report(report)
    assert not result["safe"]
    assert "restart the pods" in result["violations"]


def test_safety_checker_allows_consider_rollback() -> None:
    assert find_forbidden_actions("consider rollback if deploy correlation is confirmed") == []
