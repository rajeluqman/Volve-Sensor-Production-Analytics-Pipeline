# COST_LOG.md — Volve Sensor & Production Analytics Pipeline

> Owned by @finops-agent. Estimates only — never real account-linked $ figures.

| Item | Estimate | Source |
|------|----------|--------|
| Databricks Serverless SQL Warehouse | $400 trial credit, ~$0.15–0.40/DBU equivalent for serverless | `docs/ARCHITECTURE.md` §5 |
| Snowflake X-Small warehouse | 30-day trial | `docs/ARCHITECTURE.md` §5 |
| AWS S3 (dead — see CLAUDE.md staleness) | ~$1–5/month estimate in `docs/ARCHITECTURE.md`, but no live S3 usage in real pipeline code | `.env.example` lists buckets nothing reads |
| GitHub Codespaces | free tier, 2 core / 8GB RAM | `docs/ARCHITECTURE.md` §5 |

## Open watch items
- Databricks trial-credit burn rate not yet measured against real DBU consumption — flag if
  the $400 credit shows signs of running out before Phase 9 testing wraps.
- Snowflake 30-day trial expiry — track date once a load is actually run against it.
