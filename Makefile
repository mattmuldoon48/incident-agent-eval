.PHONY: setup test validate-eval eval eval-strict eval-v1 eval-v2 agent trace compare

PYTHON ?= python3.11
INCIDENT ?= data/incidents/incident_001.json
TRACE ?=
RUN_A ?=
RUN_B ?=

setup:
	$(PYTHON) -m venv .venv
	. .venv/bin/activate && python -m pip install -e ".[dev]"
	cp -n .env.example .env

test:
	$(PYTHON) -m pytest

validate-eval:
	$(PYTHON) scripts/run_eval.py --validate-only

eval:
	$(PYTHON) scripts/run_eval.py

eval-strict:
	$(PYTHON) scripts/run_eval.py --no-openai --fail-on-regression

eval-v1:
	$(PYTHON) scripts/run_eval.py --prompt-version triage_agent_v1

eval-v2:
	$(PYTHON) scripts/run_eval.py --prompt-version triage_agent_v2

agent:
	$(PYTHON) scripts/run_agent.py $(INCIDENT)

trace:
	@if [ -n "$(TRACE)" ]; then \
		$(PYTHON) scripts/inspect_trace.py $(TRACE); \
	else \
		$(PYTHON) scripts/inspect_trace.py --latest; \
	fi

compare:
	$(PYTHON) scripts/compare_runs.py $(RUN_A) $(RUN_B)
