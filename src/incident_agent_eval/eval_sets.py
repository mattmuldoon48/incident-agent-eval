from __future__ import annotations

from pathlib import Path

from incident_agent_eval.schemas import EvalCase
from incident_agent_eval.tool_registry import READ_ONLY_TOOLS

VALID_SEVERITIES = {"SEV-1", "SEV-2", "SEV-3", "SEV-4"}


def load_eval_cases(eval_path: Path) -> list[EvalCase]:
    return [
        EvalCase.model_validate_json(line)
        for line in eval_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_eval_cases(cases: list[EvalCase], project_root: Path) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for case in cases:
        if case.id in seen_ids:
            errors.append(f"{case.id}: duplicate eval case id")
        seen_ids.add(case.id)

        incident_path = project_root / case.incident_file
        if not incident_path.exists():
            errors.append(f"{case.id}: incident file does not exist: {case.incident_file}")

        if case.expected_severity not in VALID_SEVERITIES:
            errors.append(f"{case.id}: invalid expected severity: {case.expected_severity}")

        unknown_tools = sorted(set(case.required_tools) - set(READ_ONLY_TOOLS))
        if unknown_tools:
            errors.append(f"{case.id}: unknown required tools: {', '.join(unknown_tools)}")

        if not case.required_tools:
            errors.append(f"{case.id}: required_tools must not be empty")
        if not case.expected_likely_causes:
            errors.append(f"{case.id}: expected_likely_causes must not be empty")
        if not case.required_recommendations:
            errors.append(f"{case.id}: required_recommendations must not be empty")
        if not case.required_evidence:
            errors.append(f"{case.id}: required_evidence must not be empty")
        if not case.forbidden_actions:
            errors.append(f"{case.id}: forbidden_actions must not be empty")
    return errors


def load_and_validate_eval_cases(eval_path: Path, project_root: Path) -> list[EvalCase]:
    cases = load_eval_cases(eval_path)
    errors = validate_eval_cases(cases, project_root)
    if errors:
        raise ValueError("Invalid eval set:\n" + "\n".join(f"- {error}" for error in errors))
    return cases
