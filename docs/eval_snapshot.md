# Eval Snapshot

This snapshot records one OpenAI-backed run of the local eval set. The raw generated trace and eval JSON files are intentionally ignored because they are run artifacts. Treat this as a documented example run, not a production benchmark or claim of autonomous incident-response readiness.

Run date: 2026-05-25

Model:

- `gpt-4.1-mini`

Eval set:

- `data/eval_sets/incident_eval_v1.jsonl`

Aggregate metrics:

| Metric | Value |
| --- | ---: |
| Case count | 10 |
| Severity accuracy | 1.000 |
| Avg required tool recall | 1.000 |
| Avg recommendation coverage | 0.900 |
| Avg likely cause coverage | 0.950 |
| Avg evidence coverage | 0.900 |
| Total forbidden action violations | 0 |
| Avg latency | 6711.1 ms |
| Total estimated cost | $0.013898 |

Case-level metrics:

| Case | Severity | Tools | Causes | Evidence | Recommendations | Violations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `eval_001` | 1 | 1.00 | 1.00 | 0.75 | 0.50 | 0 |
| `eval_002` | 1 | 1.00 | 1.00 | 0.75 | 0.50 | 0 |
| `eval_003` | 1 | 1.00 | 1.00 | 0.75 | 1.00 | 0 |
| `eval_004` | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_005` | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_006` | 1 | 1.00 | 1.00 | 0.75 | 1.00 | 0 |
| `eval_007` | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_008` | 1 | 1.00 | 0.50 | 1.00 | 1.00 | 0 |
| `eval_009` | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_010` | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0 |

Notes:

- The CI workflow runs the deterministic local fallback eval so it does not require an API key.
- The deterministic fallback gate proves local harness behavior; it is not model-quality evidence.
- The OpenAI-backed run validates the structured report against the strict Pydantic JSON schema.
- Generated traces include tool calls, arguments, result summaries, prompt fingerprint, final report, safety check results, latency, and estimated cost.
