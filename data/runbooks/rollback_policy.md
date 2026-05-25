# Rollback Policy

Synthetic sample runbook for portfolio/demo purposes.

Rollback is a human-approved operational action. A read-only triage agent can identify deploy correlation and recommend considering rollback, but it cannot perform rollback.

Before rollback consideration:
- Confirm symptom onset correlates with a deploy or config rollout.
- Confirm the previous version is known-good.
- Confirm data migrations or irreversible changes are not involved.
- Get approval from the incident commander or service owner.
