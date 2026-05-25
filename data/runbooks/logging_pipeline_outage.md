# Logging Pipeline Outage Runbook

Synthetic sample runbook for portfolio/demo purposes.

## Signals

- Log ingestion lag increases.
- Indexer throttling or queue backlog appears in observability pipeline logs.
- Application traffic may remain healthy while operators lose timely visibility.

## Triage Steps

1. Confirm ingestion lag and indexer throttle rate.
2. Check whether application metrics still show healthy customer traffic.
3. Page the Observability Platform owner if delayed logs impair incident response.
4. Preserve logs and avoid deleting or disabling observability data.

## Safety

This agent must not delete logs, disable alerts, or mutate logging infrastructure.
