from pathlib import Path
from types import SimpleNamespace

import pytest
from openai import APIConnectionError

from incident_agent_eval import llm_client


ROOT = Path(__file__).resolve().parents[1]


def _context() -> dict:
    return {
        "incident": {
            "id": "incident_001",
            "service": "checkout-api",
            "summary": "Elevated 5xx errors and latency after recent deploy",
            "symptoms": ["5xx rate increased to 14%"],
            "started_at": "2026-05-24T14:05:00Z",
        },
        "metrics": [
            {
                "timestamp": "2026-05-24T14:08:00Z",
                "service": "checkout-api",
                "metric": "http_5xx_rate_pct",
                "value": 14.0,
            }
        ],
        "deploys": [],
        "logs": [],
        "runbooks": [],
        "owner": {"team": "Checkout Platform", "escalation": "checkout@example.com"},
        "severity": {"severity": "SEV-2", "explanation": "Material impact."},
        "tools_used": ["get_service_metrics"],
    }


def _settings(api_key: str | None) -> SimpleNamespace:
    return SimpleNamespace(openai_api_key=api_key, openai_model="gpt-4.1-mini", project_root=ROOT)


def test_generate_triage_report_uses_fallback_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(llm_client, "get_settings", lambda: _settings(None))

    report, usage, used_openai = llm_client.generate_triage_report(_context())

    assert report.incident_id == "incident_001"
    assert usage.input_tokens == 0
    assert not used_openai


def test_generate_triage_report_validates_prompt_version_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(llm_client, "get_settings", lambda: _settings(None))

    with pytest.raises(FileNotFoundError, match="Prompt file not found"):
        llm_client.generate_triage_report(_context(), prompt_version="missing_prompt")


def test_generate_triage_report_falls_back_on_openai_error(monkeypatch) -> None:
    class FailingCompletions:
        def create(self, **_kwargs):
            raise APIConnectionError(request=None)

    class FailingClient:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FailingCompletions())

    monkeypatch.setattr(llm_client, "get_settings", lambda: _settings("test-key"))
    monkeypatch.setattr(llm_client, "OpenAI", FailingClient)

    report, usage, used_openai = llm_client.generate_triage_report(_context())

    assert report.incident_id == "incident_001"
    assert any("OpenAI API call failed" in note for note in report.safety_notes)
    assert usage.input_tokens == 0
    assert not used_openai
