# ADR-002: SQL Warehouse only — no classic cluster

**Status:** Accepted | **Date:** original (per `docs/ARCHITECTURE.md` v2.0)

> Migrated verbatim from `docs/ARCHITECTURE.md` §6 by the 2026-06-29 governance retrofit —
> real rationale already existed there, not reconstructed.

## Decision
All ETL runs on Databricks SQL Warehouse. No classic compute clusters provisioned.

## Why
Classic clusters consume the $400 trial credit quickly (~$0.15–0.40/DBU). SQL Warehouse
Serverless is more cost-efficient for SQL workloads and sufficient for this dataset size.

## Implication
PySpark API is not available — all transforms are written as SQL DDL/DML executed via
`databricks-sql-connector` from Codespaces (`bronze/*.py`, `silver/*.py`, `gold/*.py`). This is
the basis for `tests/boundary_contract.py` ST1 (no `pyspark` import anywhere in live pipeline
code).
