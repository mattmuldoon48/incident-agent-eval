# Database Connection Pool Runbook

Synthetic sample runbook for portfolio/demo purposes.

Symptoms include connection pool exhaustion, database connection timeout, and elevated application 5xx responses.

Read-only triage steps:
- Inspect timeout rate and pool saturation metrics.
- Search application logs for connection acquisition timeout messages.
- Correlate onset with deploys that changed query patterns, transaction scope, or pool settings.
- Escalate to the service owner and database support path when user impact is material.
