import json
from pathlib import Path

import pytest

from incident_agent_eval import tools
from incident_agent_eval.tool_registry import MUTATING_TOOL_KEYWORDS, READ_ONLY_TOOLS, assert_read_only_registry
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


@pytest.mark.parametrize(
    ("reader", "filename", "extra_args"),
    [
        (get_service_metrics, "metrics.jsonl", {}),
        (get_recent_deploys, "deploys.jsonl", {}),
        (search_logs, "logs.jsonl", {"query": "timeout"}),
    ],
)
def test_observability_filters_service_and_inclusive_time_window(
    tmp_path: Path, monkeypatch, reader, filename: str, extra_args: dict
) -> None:
    data_dir = tmp_path / "data" / "mock_observability"
    data_dir.mkdir(parents=True)
    rows = [
        {
            "id": row_id,
            "service": service,
            "timestamp": timestamp,
            "message": "database timeout",
        }
        for row_id, service, timestamp in [
            ("stale", "checkout-api", "2026-05-24T12:59:59Z"),
            ("start", "checkout-api", "2026-05-24T15:00:00+02:00"),
            ("end", "checkout-api", "2026-05-24T14:30:00Z"),
            ("future", "checkout-api", "2026-05-24T14:30:01Z"),
            ("other-service", "billing-api", "2026-05-24T14:00:00Z"),
        ]
    ]
    (data_dir / filename).write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(tools, "_root", lambda: tmp_path)

    results = reader("checkout-api", time_window_minutes=90, **extra_args)

    assert [row["id"] for row in results] == ["start", "end"]
