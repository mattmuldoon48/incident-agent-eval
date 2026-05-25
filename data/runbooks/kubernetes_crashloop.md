# Kubernetes CrashLoopBackOff Runbook

Synthetic sample runbook for portfolio/demo purposes.

Use this runbook when pods repeatedly fail startup or readiness checks.

Read-only triage steps:
- Search logs for startup exceptions, missing environment variables, and invalid config.
- Check recent deploy or configuration rollout events.
- Compare ready pod count against desired replicas.
- Page the owning team if availability is degraded.

This agent may recommend human review of rollback eligibility, but it must not restart pods or change Kubernetes resources.
