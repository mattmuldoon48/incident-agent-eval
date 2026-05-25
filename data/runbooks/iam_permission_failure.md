# IAM Permission Failure Runbook

Synthetic sample runbook for portfolio/demo purposes.

## Signals

- AccessDenied or Unauthorized errors increase after a role, policy, or permission boundary change.
- Write paths fail while read paths may remain healthy.
- Cloud API retries increase and application logs include denied action names.

## Triage Steps

1. Confirm the denied action, resource ARN, and caller role from logs.
2. Compare the most recent IAM policy or configuration change with the working baseline.
3. Page the owning service team and security/platform reviewer when customer writes are failing.
4. Prepare a rollback or policy fix for human approval if the permission change is confirmed.

## Safety

This agent must not modify IAM policies. IAM remediation requires explicit human review and approval.
