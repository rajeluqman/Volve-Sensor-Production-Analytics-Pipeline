# Start Here — Volve Sensor & Production Analytics Pipeline

> **Week-1 reader? Read this page first.** It answers *why this pipeline exists, what business
> questions it answers, and what's actually proven* — before you open any other doc. The rest of
> this space mirrors the repo's real docs, including their known staleness.

## What is this pipeline?

An end-to-end data-engineering pipeline on the **public Equinor Volve** North Sea oil-field
dataset. It turns raw, multi-format upstream data (Excel production reports + WITSML XML
trajectory/sensor logs) into a **trustworthy, queryable analytics product** served through
Snowflake BI views — Bronze → Silver → Gold on Databricks SQL Warehouse, with a DQ gate, ML
feature store, and an Airflow DAG.

## Why it exists (purpose)

A production-grade DE portfolio project. **Consumer:** a (simulated) production-engineering /
reservoir-ops team, via the Snowflake serving views. **Decision it supports:** daily "which
wells need attention, and why" monitoring + forward-looking pressure/efficiency signals.

## Business questions it answers

1. **Which wells show production anomalies today** (pressure/water-cut spikes, zero-production
   while on-stream, GOR anomalies)? → `vw_anomaly_alerts`
2. **What is next-day downhole pressure** likely to be? → `volve_pressure_prediction` → `vw_ml_predictions`
3. **How does efficiency compare across wells / over time?** → `vw_well_comparison`, `vw_production_trends`
4. **Is the production record trustworthy** before BI? → Silver DQ gate (`check_dq_silver`, blocks if < 95%)

## What's proven vs not (read before trusting numbers)

- **Verifiable:** 3 wells (F-1/F-11/F-12) of 29, 4,967 production records (2007–2016), 5 BI
  views, 3 ML models defined, a real inline-SQL DQ gate in the DAG.
- **NOT yet captured:** run-evidence (model metrics, anomaly counts, DQ pass rates, screenshots).
  No metrics are fabricated — see README "Results & Evidence".
- **Known false claims, corrected:** earlier "Great Expectations suites" / "84 tests, 0 failures"
  are **unsupported** (`data_quality/` and `tests/` are stub-only). See `INTERVIEW_GUIDE.md`.

## Reading order (full doc set)

1. **README.md** — overview, real stack, business questions, build status
2. **CLAUDE.md** — AI/governance context; the "Known doc staleness" section is the single most
   important thing to read before trusting any other doc here
3. **docs/ARCHITECTURE.md** (v2.0) — doc-of-record for stack/architecture
4. **docs/DATA_MODEL.md** + **docs/DATA_DICTIONARY.md** — grain doctrine, column reference
5. **docs/ADR/** — ADR-001–007 (migrated from ARCHITECTURE.md §6, real rationale), ADR-008
   (identity grain, new), ADR-009 (ML model selection, reconstructed — flagged for owner confirm)
6. **docs/BRD.md, DRD.md, PIPELINE_SPEC.md, DQD.md** — kept for history, all **stale v1.0**
   (describe an abandoned NiFi+AWS Glue+GE design). Cross-check against ARCHITECTURE.md or the
   real code before relying on them.
7. **INTERVIEW_GUIDE.md** — resume-claim ↔ repo-evidence reconciliation
8. **PROJECT_STATUS.md** — current build state

Synced via `scripts/sync_docs_to_confluence.py` (manual run, not CI-wired).
