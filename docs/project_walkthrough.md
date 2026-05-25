# Project Walkthrough

This project demonstrates a bounded, evaluated AI agent for local cloud incident triage. It is intentionally not a production incident platform; all incidents, metrics, logs, deploys, owners, and runbooks are synthetic local files.

## Demo Path

Run the deterministic local path first:

```bash
make test
make validate-eval
incident-eval --list-cases
make eval-strict
make eval-case CASE_ID=eval_001
make agent INCIDENT=data/incidents/incident_001.json
make trace
```

Then, with `OPENAI_API_KEY` set in `.env`, run:

```bash
make eval
python scripts/run_eval.py --prompt-version triage_agent_v2
```

To compare two eval reports:

```bash
python scripts/compare_runs.py reports/eval_runs/run_a.json reports/eval_runs/run_b.json
```

## System Behavior

The agent follows a fixed sequence:

1. Load incident JSON.
2. Read service metrics from local JSONL.
3. Read recent deploy events from local JSONL.
4. Search local logs.
5. Search synthetic markdown runbooks.
6. Read local service ownership data.
7. Classify severity with deterministic rules.
8. Ask the configured OpenAI model for a structured triage report, or use deterministic fallback.
9. Validate the report with Pydantic.
10. Run safety checks against destructive operational language.
11. Save a trace with tools, arguments, results, safety status, latency, and estimated cost.

## Key Design Decisions

- Bounded tool use: the agent cannot choose arbitrary tools or mutate systems.
- Read-only data: all tools read local mock data and return evidence.
- Structured output: final reports must match the `TriageReport` schema.
- Safety after generation: guardrails inspect the final artifact users would act on.
- Eval-first workflow: prompt and behavior changes are judged by regression metrics.
- CI without secrets: deterministic fallback keeps tests and evals runnable in GitHub Actions.

## Eval Story

The five-case eval set covers checkout, payments, auth, search, and reporting scenarios. It scores:

- severity correctness
- required tool recall
- likely cause coverage
- evidence coverage
- recommendation coverage
- forbidden action violations
- latency
- estimated cost

Regression thresholds are enforced by:

```bash
python scripts/run_eval.py --fail-on-regression
```

The committed OpenAI-backed snapshot is in [`eval_snapshot.md`](eval_snapshot.md).

## Safety Story

The safety layer flags destructive or overreaching operational language, including rollback claims, pod restarts, pod deletion, automatic scaling, alert disabling, IAM changes, and log deletion.

Allowed recommendations include paging owners, checking logs, reviewing metrics, and considering rollback only after human confirmation. The agent never performs actions.

## Interview Talking Points

- Why fixed tool sequencing is appropriate for a portfolio MVP.
- How local mock data makes the project reproducible and safe.
- Why final-output safety checks matter more than prompt-only safety.
- How evidence coverage exposes whether outputs are grounded in retrieved context.
- How prompt versions can be compared with the same eval harness.
- How fallback behavior keeps CI reliable while preserving the real OpenAI path.
