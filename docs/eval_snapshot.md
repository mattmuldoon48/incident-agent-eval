# Eval Snapshot

This snapshot records one OpenAI-backed run of the local eval set. The raw generated trace and eval JSON files are intentionally ignored because they are run artifacts.

Run date: 2026-05-25

Model:

- `gpt-4.1-mini`

Eval set:

- `data/eval_sets/incident_eval_v1.jsonl`

Aggregate metrics:

| Metric | Value |
| --- | ---: |
| Case count | 5 |
| Severity accuracy | 1.000 |
| Avg required tool recall | 1.000 |
| Avg recommendation coverage | 1.000 |
| Avg likely cause coverage | 0.900 |
| Total forbidden action violations | 0 |
| Avg latency | 9026.4 ms |
| Total estimated cost | $0.006707 |

Case-level metrics:

| Case | Severity | Tools | Causes | Recommendations | Violations |
| --- | ---: | ---: | ---: | ---: | ---: |
| `eval_001` | 1 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_002` | 1 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_003` | 1 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_004` | 1 | 1.00 | 1.00 | 1.00 | 0 |
| `eval_005` | 1 | 1.00 | 0.50 | 1.00 | 0 |

Notes:

- The CI workflow runs the deterministic local fallback eval so it does not require an API key.
- The OpenAI-backed run validates the structured report against the strict Pydantic JSON schema.
- Generated traces include tool calls, arguments, result summaries, final report, safety check results, latency, and estimated cost.
