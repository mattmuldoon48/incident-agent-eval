from incident_agent_eval import tools


READ_ONLY_TOOLS = {
    "get_service_metrics": tools.get_service_metrics,
    "search_logs": tools.search_logs,
    "get_recent_deploys": tools.get_recent_deploys,
    "get_service_owner": tools.get_service_owner,
    "search_runbooks": tools.search_runbooks,
    "classify_severity": tools.classify_severity,
}

MUTATING_TOOL_KEYWORDS = ("rollback", "restart", "delete", "scale", "update", "create_ticket", "modify")


def assert_read_only_registry() -> None:
    bad = [name for name in READ_ONLY_TOOLS if any(keyword in name for keyword in MUTATING_TOOL_KEYWORDS)]
    if bad:
        raise ValueError(f"Mutating tools are not allowed: {bad}")
