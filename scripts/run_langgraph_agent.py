from __future__ import annotations

import argparse

from incident_agent_eval.langgraph_runner import run_langgraph_agent
from incident_agent_eval.llm_client import TRIAGE_PROMPT_VERSION
from incident_agent_eval.report import print_triage_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one incident through optional LangGraph orchestration.")
    parser.add_argument("incident_file", help="Path to incident JSON file.")
    parser.add_argument(
        "--prompt-version",
        default=TRIAGE_PROMPT_VERSION,
        help="Prompt file stem from prompts/, for example triage_agent_v1.",
    )
    parser.add_argument(
        "--no-openai",
        action="store_true",
        help="Force deterministic fallback generation even when OPENAI_API_KEY is set.",
    )
    args = parser.parse_args()
    trace, trace_path = run_langgraph_agent(
        args.incident_file,
        prompt_version=args.prompt_version,
        use_openai=not args.no_openai,
    )
    print_triage_report(trace, str(trace_path))


if __name__ == "__main__":
    main()
