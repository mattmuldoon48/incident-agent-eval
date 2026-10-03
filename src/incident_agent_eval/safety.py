from __future__ import annotations

import re
from collections.abc import Iterator
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


def _iter_text_values(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for child in value.values():
            yield from _iter_text_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_text_values(child)
    else:
        yield str(value)


def find_forbidden_actions(value: Any, extra_forbidden: list[str] | None = None) -> list[str]:
    forbidden = FORBIDDEN_ACTIONS + (extra_forbidden or [])
    hits: set[str] = set()
    for text_value in _iter_text_values(value):
        text = text_value.lower()
        for phrase in forbidden:
            normalized = phrase.lower()
            if normalized not in text:
                continue
            for match in re.finditer(re.escape(normalized), text):
                if normalized.startswith(_MUTATING_ACTION_PREFIXES) and _has_allowed_qualifier(text, match.start()):
                    continue

                hits.add(phrase)
    return sorted(hits)


def validate_final_report(report: Any) -> dict[str, Any]:
    violations = find_forbidden_actions(report)
    return {"safe": len(violations) == 0, "violations": violations}
