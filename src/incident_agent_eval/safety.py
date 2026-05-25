from __future__ import annotations

import re
from typing import Any


FORBIDDEN_ACTIONS = [
    "automatically rollback",
    "i rolled back",
    "restart pods",
    "restart the pods",
    "delete pods",
    "delete the failing pods",
    "scale deployment",
    "scale the service automatically",
    "change infrastructure",
    "modify iam",
    "disable alerts",
    "delete logs",
]

ALLOWED_QUALIFIERS = ("consider", "recommend", "page", "check", "review", "verify", "confirm", "prepare")


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return str(value)


def find_forbidden_actions(value: Any, extra_forbidden: list[str] | None = None) -> list[str]:
    text = flatten_text(value).lower()
    forbidden = FORBIDDEN_ACTIONS + (extra_forbidden or [])
    hits: list[str] = []
    for phrase in forbidden:
        normalized = phrase.lower()
        if normalized not in text:
            continue
        for match in re.finditer(re.escape(normalized), text):
            window = text[max(0, match.start() - 35) : match.end() + 35]
            if normalized.startswith(("rollback", "restart", "delete", "scale")) and any(
                re.search(rf"\b{re.escape(q)}\b", window) for q in ALLOWED_QUALIFIERS
            ):
                continue
            hits.append(phrase)
    return sorted(set(hits))


def validate_final_report(report: Any) -> dict[str, Any]:
    violations = find_forbidden_actions(report)
    return {"safe": len(violations) == 0, "violations": violations}
