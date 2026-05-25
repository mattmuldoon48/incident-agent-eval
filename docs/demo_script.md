# Demo Script

Use this when walking through the project in an interview, portfolio review, or recorded demo. The goal is to show that this is an evaluated, bounded AI system rather than a chatbot demo.

## 60-Second Pitch

Incident Agent Eval is a local, read-only AI incident triage agent. It takes a synthetic cloud incident, gathers evidence from mock metrics, logs, deploys, ownership data, and runbooks, then produces a structured triage report with severity, likely causes, evidence, next actions, escalation target, and safety notes.

The important engineering choices are the fixed read-only tool sequence, Pydantic structured outputs, full trace persistence, destructive-action safety checks, deterministic fallback mode, and regression evals over realistic incident scenarios.

## Five-Minute Demo

Start with a sanity check:

```bash
make doctor
```

Point out:

- required local data and prompt files are present
- `OPENAI_API_KEY` status is shown without revealing the key
- the project can run with deterministic fallback if no key is set

Run the test and regression gate:

```bash
make lint
make test
make eval-strict
```

Point out:

- tests cover schemas, tools, safety, eval scoring, trace inspection, and CLI helpers
- strict eval uses `--no-openai` so CI does not require secrets
- thresholds fail the command if quality regresses

Run one incident:

```bash
python scripts/run_agent.py data/incidents/incident_001.json --no-openai
```

Point out:

- the report includes severity, likely causes, evidence, next actions, escalation, and customer update text
- the agent recommends human follow-up but does not execute remediation
- every run saves a trace

Inspect the latest trace:

```bash
python scripts/inspect_trace.py --latest
```

Point out:

- tool calls, arguments, result summaries, final report, safety result, latency, and cost are persisted
- tracing makes behavior reviewable after the fact

Show eval diagnostics:

```bash
python scripts/run_eval.py --no-openai --fail-on-regression
```

Then open `reports/eval_runs/latest.md` locally and point out:

- aggregate metrics
- per-case scores
- missing tools
- missed likely causes
- missed evidence
- missed recommendations
- forbidden action matches

Generated eval reports are intentionally ignored by git.

## OpenAI-Backed Demo

With `.env` configured:

```bash
python scripts/run_eval.py --fail-on-regression
```

Point out:

- the model path still validates the final report against the same Pydantic schema
- if the API call fails, the agent records a safety note and falls back deterministically
- `docs/eval_snapshot.md` captures a committed example of an OpenAI-backed run

## Design Questions To Be Ready For

Why use a fixed tool sequence?

The project is optimizing for bounded, reviewable behavior. For incident triage, a constrained evidence-gathering path is easier to test, trace, and safety-check than an open-ended autonomous loop.

Why local mock data?

It keeps the project safe, reproducible, and portfolio-friendly. There is no real infrastructure access and no chance of mutating production systems.

Why final-output safety checks?

The final report is the artifact a human might act on. Checking only the prompt would miss unsafe language introduced by model generation or fallback logic.

What makes this an eval project?

Behavior changes are scored across a reusable JSONL eval set. The runner checks severity, required tools, likely causes, evidence, recommendations, forbidden actions, latency, and cost.

What would productionization require?

Real integrations would need authentication, tenant boundaries, observability API clients, audit logs, rate limits, data retention policies, human approval workflows, and much deeper eval coverage. This repo intentionally stops before those concerns.
