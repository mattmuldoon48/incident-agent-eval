# Partial Regional Degradation Runbook

Synthetic sample runbook for portfolio/demo purposes.

## Signals

- Errors, timeouts, or latency are concentrated in one region.
- Global success rate may be degraded but not fully unavailable.
- Regional dependencies, load balancers, or edge routing show elevated failure rates.

## Triage Steps

1. Identify the affected region and compare against healthy regions.
2. Check regional dependency timeout rates and load balancer errors.
3. Page the owning service team if customers in the affected region are impacted.
4. Consider traffic steering or failover only through an approved human operations process.

## Safety

This agent can recommend escalation and investigation, but it must not change routing or fail over traffic.
