# Security

This is a local portfolio project using synthetic incident data and mock read-only tools. It does not connect to real cloud infrastructure, Kubernetes clusters, observability platforms, PagerDuty, Slack, databases, or ticketing systems.

## Secrets

Do not commit `.env` or real API keys. The repository includes `.env.example` only.

The OpenAI API key is read from:

```bash
OPENAI_API_KEY=
```

Generated traces and eval reports are local run artifacts and are gitignored.

## Tool Safety

All implemented tools are read-only. The project intentionally excludes tools that rollback, restart, delete, scale, modify IAM, disable alerts, create tickets, or mutate infrastructure.

## Reporting Issues

If you find a security issue in this portfolio project, open a private GitHub security advisory or contact the repository owner directly.
