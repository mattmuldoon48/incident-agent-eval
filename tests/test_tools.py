from incident_agent_eval.tool_registry import READ_ONLY_TOOLS, MUTATING_TOOL_KEYWORDS, assert_read_only_registry
from incident_agent_eval.tools import get_recent_deploys, get_service_metrics, search_logs, search_runbooks


def test_tools_read_mock_data() -> None:
    assert get_service_metrics("checkout-api", 90)
    assert search_logs("checkout-api", "timeout", 90)
    assert get_recent_deploys("checkout-api", 90)
    assert search_runbooks("5xx latency")


def test_no_mutating_tools_exist_in_registry() -> None:
    assert_read_only_registry()
    for tool_name in READ_ONLY_TOOLS:
        assert not any(keyword in tool_name for keyword in MUTATING_TOOL_KEYWORDS)
