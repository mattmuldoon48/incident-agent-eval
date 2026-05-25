# Elevated 5xx Runbook

Synthetic sample runbook for portfolio/demo purposes.

Use this runbook when a service has a sustained increase in HTTP 5xx responses.

Read-only triage steps:
- Check service metrics for error rate, p95 latency, and saturation.
- Search logs for common exception classes and upstream timeout messages.
- Check recent deploys or configuration changes that correlate with the alert.
- Page the service owner for SEV-1 or SEV-2 customer-impacting incidents.

Do not execute rollback, restart, scaling, deletion, or configuration mutation from this agent.
