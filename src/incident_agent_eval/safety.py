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

ALLOWED_QUALIFIERS = (
    "consider",
    "recommend",
    "page",
    "check",
    "review",
    "verify",
    "confirm",
    "prepare",
    "do not",
    "must not",
    "avoid",
)

_MUTATING_ACTION_PREFIXES = ("rollback", "restart", "delete", "scale", "disable", "change", "modify")

_ALLOWED_QUALIFIER_RE = re.compile(
    rf"\b(?:{'|'.join(re.escape(qualifier) for qualifier in ALLOWED_QUALIFIERS)})\s+(?:that\s+)?$"
)
_COORDINATED_NEGATION_RE = re.compile(
    rf"\b(?:do not|must not|avoid)\s+(?:{'|'.join(re.escape(action) for action in FORBIDDEN_ACTIONS if action.startswith(_MUTATING_ACTION_PREFIXES))})\s+(?:and|or)\s+$"
)


def _has_allowed_qualifier(text: str, action_start: int) -> bool:
    return any(
        pattern.search(text, 0, action_start) is not None
        for pattern in (_ALLOWED_QUALIFIER_RE, _COORDINATED_NEGATION_RE)
    )


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
            if normalized.startswith(_MUTATING_ACTION_PREFIXES) and _has_allowed_qualifier(text, match.start()):
                continue

            hits.append(phrase)
    return sorted(set(hits))


def validate_final_report(report: Any) -> dict[str, Any]:
    violations = find_forbidden_actions(report)
    return {"safe": len(violations) == 0, "violations": violations}
