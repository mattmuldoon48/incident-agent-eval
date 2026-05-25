# API Latency Runbook

Synthetic sample runbook for portfolio/demo purposes.

Use this runbook when p95 or p99 latency increases beyond baseline.

Read-only triage steps:
- Compare current latency with recent baseline metrics.
- Check dependency timeout logs and connection pool saturation signals.
- Review deploys that changed data access, network calls, or validation logic.
- Draft a customer update when the impact is user-visible.
