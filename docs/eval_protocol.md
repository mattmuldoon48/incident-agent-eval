# Eval Protocol

This project uses a small, local eval protocol for a bounded incident triage harness. It is designed for portfolio review and regression testing, not for claiming production incident-response readiness.

## Scope

- Eval data is local and synthetic.
- Incident cases live in `data/eval_sets/incident_eval_v1.jsonl`.
- Each case points to one local incident JSON file under `data/incidents/`.
- The eval runner executes the same fixed read-only tool sequence as a normal run.
- Generated JSON, CSV, Markdown reports, and traces are local run artifacts under `reports/` and are intentionally ignored by git.

## Incident File Format

Each incident JSON file is validated as an `IncidentInput`. Required fields are `id`, `service`, `summary`, `symptoms`, and `started_at`; `symptoms` is a list of observed signals, and `started_at` should be an ISO timestamp such as `2026-05-24T14:05:00Z`.

## Eval Case Format

Each JSONL row is validated as an `EvalCase`. Required fields are `id`, `incident_file`, `expected_severity`, `required_tools`, `expected_likely_causes`, `required_recommendations`, `required_evidence`, and `forbidden_actions`; `incident_file` points to a local incident JSON path, and `expected_severity` must be one of `SEV-1` through `SEV-4`.

Before adding a case, run validation-only mode to catch duplicate IDs, missing incident files, invalid severities, unknown tool names, and empty expected lists without generating traces or reports:

```bash
python scripts/run_eval.py --validate-only
```

## Run Selected Incident Cases

These commands use the original incident JSONL evaluator, not the security-comparison command `python -m incident_agent_eval.run_eval`. Run them from the repository root after setup:

```bash
python scripts/run_eval.py --list-cases
python scripts/run_eval.py --case-id eval_001 --case-id eval_003 --validate-only
python scripts/run_eval.py --no-openai --case-id eval_001 --case-id eval_003
```

Repeat `--case-id` to select multiple eval IDs, not incident IDs. Selected cases retain dataset order, repeated IDs run only once, and unknown IDs fail. Omit the option to run the full set. `--no-openai` forces deterministic local generation even when an API key is configured.

Use `--eval-set PATH` for another incident-eval JSONL file; relative paths resolve against the project root. The entire file and its referenced incidents are validated **before** filtering, so an invalid unselected case still fails. Listing and validation create no traces or evaluation reports; the validation success count reflects the selected cases.

A filtered run's metrics and threshold checks cover only its selected cases. It replaces the same `reports/eval_runs/latest.json`, `latest.csv`, and `latest.md` as a full run; retain the timestamped report printed by the command when preserving a full-suite result.

## Incident Eval Metrics

For each eval case, the runner produces one `EvalResult`.

- **Severity correctness**: `1` if the final report severity exactly equals `expected_severity`, otherwise `0`.
- **Required tool recall**: successful required read-only tool calls in the trace divided by required tools in the eval case.
- **Likely cause coverage**: expected likely-cause phrases matched against `final_report.likely_causes` by exact substring or token-overlap heuristic.
- **Recommendation coverage**: required recommendation phrases matched against `final_report.recommended_next_actions` by exact substring or token-overlap heuristic.
- **Evidence coverage**: required evidence phrases matched against final evidence source, quote/summary, and relevance text.
- **Forbidden action violations**: destructive or overreaching operational phrases found in the final report.
- **Latency**: measured local runtime for the agent run.
- **Estimated cost**: OpenAI token-cost estimate when a model call is used; deterministic fallback runs have zero model token cost.

Aggregate metrics are simple averages or totals across the selected cases.

## Thresholds

The default regression thresholds are defined in `src/incident_agent_eval/evaluators.py` and are used by `python scripts/run_eval.py --fail-on-regression` and `make eval-strict`.

The deterministic fallback path is the CI/local regression gate. It exists so the repo can be verified without secrets or network calls. It should not be presented as independent model-quality evidence.

## OpenAI Snapshot

`docs/eval_snapshot.md` records one checked-in OpenAI-backed eval snapshot. It is a documented example run, not a live benchmark service and not a claim of production readiness. Do not change those numbers unless they are directly supported by a new checked-in snapshot.

## Metric Caveats

- Coverage metrics are deterministic text checks, not human grading.
- The eval set has 10 starter cases, so aggregate scores are useful for regression but not statistically broad.
- Mock logs, metrics, deploys, owners, runbooks, and incidents are synthetic.
- The fixed tool sequence is deliberate: it makes evals repeatable and traceable, but it does not demonstrate open-ended autonomous planning.
