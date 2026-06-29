# ADR-006: Docker Airflow instead of MWAA

**Status:** Accepted | **Date:** original (per `docs/ARCHITECTURE.md` v2.0)

> Migrated verbatim from `docs/ARCHITECTURE.md` §6 by the 2026-06-29 governance retrofit —
> real rationale already existed there, not reconstructed.

## Decision
Apache Airflow runs in Docker on Codespaces (`infrastructure/docker-compose.yml`,
LocalExecutor), not Amazon MWAA.

## Why
MWAA costs ~$50/month minimum. Docker Airflow is free, uses identical DAG code, and is
sufficient for portfolio demonstration. The DAG structure and task definitions
(`airflow/dags/volve_daily_pipeline.py`) are directly portable to MWAA or any managed Airflow
provider.

## Consequence
8GB Codespaces RAM means Airflow Docker and NiFi Docker cannot run concurrently
(`docs/ARCHITECTURE.md` §5) — moot in practice since NiFi was never built (ADR-001), but the
RAM-ceiling lesson applies to any future concurrent-service proposal. See `airflow/MWAA_SETUP.txt`
for the (unexercised) MWAA migration path.
