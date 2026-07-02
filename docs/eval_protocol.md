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
