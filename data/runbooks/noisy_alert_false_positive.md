# Noisy Alert False Positive Runbook

Synthetic sample runbook for portfolio/demo purposes.

## Signals

- A synthetic canary or single probe fails briefly.
- Customer-facing metrics remain within baseline.
- Error budget burn, latency, and delivery success metrics do not confirm impact.

## Triage Steps

1. Verify customer-facing metrics before declaring an incident.
2. Compare synthetic probe failures with application logs and real user traffic.
3. Notify the owning team if alert noise repeats.
4. Review alert threshold tuning after confirming the signal is a false positive.

## Safety

This agent must not disable alerts. Alert tuning requires human review.
