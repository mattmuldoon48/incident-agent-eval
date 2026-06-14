# Optional LangGraph Mode

LangGraph was added as an optional orchestration implementation for learning and comparison. The default deterministic runner still exists because this small workflow benefits from a fixed, inspectable tool sequence and reproducible eval behavior.

This is not a production LangGraph system, enterprise deployment, or autonomous remediation platform. It is a bounded read-only workflow over synthetic local data.

## Graph Mapping

`src/incident_agent_eval/langgraph_runner.py` models the existing triage path as explicit graph nodes:

1. `load_incident`
2. `get_metrics`
3. `get_recent_deploys`
4. `search_logs`
5. `search_runbooks`
6. `get_service_owner`
7. `classify_severity`
8. `generate_report`
9. `safety_check`
10. `save_trace`

The graph state carries the incident input, tool results, final report, safety result, accumulated `ToolCall` trace data, and errors. Tool nodes call the same read-only functions from `READ_ONLY_TOOLS`; no mutating tools are introduced.

## Difference From The Deterministic Runner

The deterministic runner in `src/incident_agent_eval/agent.py` executes the same fixed sequence directly in Python. The LangGraph runner expresses that sequence as graph nodes and state transitions, then emits the same `AgentTrace` contract used by trace inspection and eval scoring.

The graph mode adds orchestration structure; it does not change the tool set, connect to external infrastructure, or claim better benchmark results.

## Why The Fixed Runner Still Exists

The fixed runner remains the default because it is simpler, has fewer optional dependencies, and is easier to reason about for this small workflow. Keeping it prevents the project from implying that LangGraph is required where straightforward deterministic control flow is enough.

## Run One Incident

Install the optional extra:

```bash
pip install -e ".[langgraph]"
```

Run one incident:

```bash
python scripts/run_langgraph_agent.py data/incidents/incident_001.json
```

For a local deterministic report without an OpenAI call:

```bash
python scripts/run_langgraph_agent.py data/incidents/incident_001.json --no-openai
```

The saved trace includes `orchestration_mode = "langgraph"`.

## Run The LangGraph Eval

```bash
python scripts/run_langgraph_eval.py
```

The script runs the existing incident eval set through the LangGraph runner, computes the same metrics as the normal eval, and writes reports under `reports/eval_runs/` with `orchestration_mode = "langgraph"`.

Use this command for an offline deterministic eval run:

```bash
python scripts/run_langgraph_eval.py --no-openai
```

## Remaining Limitations

- All incidents, logs, metrics, deploys, owners, and runbooks are synthetic local files.
- The tools are read-only and do not call AWS, Kubernetes, PagerDuty, Slack, Datadog, databases, or ticketing systems.
- The graph is a fixed workflow, not an autonomous planner.
- Eval metrics are deterministic checks over the trace and report, not evidence of production readiness.
- LangGraph is optional; the project still supports the dependency-light deterministic runner.
