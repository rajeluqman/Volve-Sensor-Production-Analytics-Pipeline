# REPO_MAP — generated navigation index

> **GENERATED — do not hand-edit.** `python scripts/gen_repo_map.py` rebuilds it from
> ground truth; CI runs `--check` and fails if this file is stale. Purpose is extracted
> from each file's own docstring / first heading / leading comment; *Uses* and *Used by*
> are parsed (`ast` for Python, `ref()` for dbt), never authored.
>
> **This is a pointer, not a cache.** It tells you which file to open — then READ THAT
> FILE FRESH before you edit or assert about it (ANTI-SHORTCUT PROTOCOL, CLAUDE.md).

**81 files mapped.**

## Architecture Decision Records

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `docs/ADR/ADR-001-skip-nifi-glue-ingestion.md` | ADR-001: Skip NiFi + AWS Glue ingestion | — | — |
| `docs/ADR/ADR-002-sql-warehouse-only.md` | ADR-002: SQL Warehouse only — no classic cluster | — | — |
| `docs/ADR/ADR-003-witsml-json-serialization.md` | ADR-003: TO_JSON() for WITSML nested structs | — | — |
| `docs/ADR/ADR-004-delta-lake-table-format.md` | ADR-004: Delta Lake as table format | — | — |
| `docs/ADR/ADR-005-three-well-scope.md` | ADR-005: 3 wells only (F-1, F-11, F-12) | — | — |
| `docs/ADR/ADR-006-docker-airflow.md` | ADR-006: Docker Airflow instead of MWAA | — | — |
| `docs/ADR/ADR-007-excel-header-workaround.md` | ADR-007: Excel header row workaround | — | — |
| `docs/ADR/ADR-008-identity-grain.md` | ADR-008: Identity grain — (well_id, DATEPRD) production, (well_id, md_m) trajectory, no dbt/no SCD | — | — |
| `docs/ADR/ADR-009-ml-model-selection.md` | ADR-009: ML model selection — XGBoost / Random Forest / Isolation Forest | — | — |

## Top-level docs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `COST_LOG.md` | COST_LOG.md — Volve Sensor & Production Analytics Pipeline | — | — |
| `DECISION_LOG.md` | DECISION_LOG.md — Volve Sensor & Production Analytics Pipeline (governance retrofit) | — | — |
| `INFRA_LIMITS_LOG.md` | INFRA_LIMITS_LOG.md — Volve Sensor & Production Analytics Pipeline | — | — |
| `INTERVIEW_GUIDE.md` | INTERVIEW_GUIDE.md — Volve Sensor & Production Analytics Pipeline | — | — |
| `README.md` | Volve Sensor & Production Analytics Pipeline | — | — |
| `docs/ARCHITECTURE.md` | ARCHITECTURE.md — Solution Architecture | — | — |
| `docs/BRD.md` | BRD — Business Requirements Document | — | — |
| `docs/DATA_DICTIONARY.md` | DATA_DICTIONARY.md | — | — |
| `docs/DATA_MODEL.md` | DATA_MODEL.md — Grain & Table Doctrine | — | — |
| `docs/DQD.md` | DQD — Data Quality Document | — | — |
| `docs/DRD.md` | DRD — Data Requirements Document | — | — |
| `docs/OPS_RUNBOOK.md` | OPS_RUNBOOK.md — Operations Runbook | — | — |
| `docs/PIPELINE_SPEC.md` | PIPELINE_SPEC.md — Pipeline Specification | — | — |

## Bronze ingestion

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `bronze/bronze_production.py` | Bronze Layer — Production Data | — | — |
| `bronze/bronze_witsml.py` | Bronze Layer — WITSML Realtime Drilling Data (Trajectory) | — | — |
| `bronze/glue_jobs/HOW_IT_WORKS.txt` | — | — | — |
| `bronze/run_bronze.py` | Bronze Layer — Orchestrator | — | — |

## Silver transforms

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `silver/notebooks/DATABRICKS_SETUP.txt` | — | — | — |
| `silver/notebooks/HOW_IT_WORKS.txt` | — | — | — |
| `silver/run_silver.py` | Silver Layer — Orchestrator | — | — |
| `silver/silver_production.py` | Silver Layer — Production Data | — | — |
| `silver/silver_trajectory.py` | Silver Layer — WITSML Trajectory Data | — | — |

## Gold KPIs / feature store (no dbt)

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `gold/gold_ml_features.py` | Gold Layer — ML Feature Store | — | run_gold.py |
| `gold/gold_production_daily.py` | Gold Layer — Production Daily KPIs | — | run_gold.py |
| `gold/notebooks/DATABRICKS_SETUP.txt` | — | — | — |
| `gold/notebooks/HOW_IT_WORKS.txt` | — | — | — |
| `gold/run_gold.py` | Gold Layer Orchestrator | gold_ml_features.py, gold_production_daily.py | — |

## ML training + scoring (MLflow)

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `ml/run_ml.py` | ML Layer Orchestrator | train_anomaly_detection.py, train_drilling_efficiency.py, train_pressure_prediction.py | — |
| `ml/score_models.py` | ML Scoring — Batch Inference | — | — |
| `ml/train_anomaly_detection.py` | ML Model 3 — Anomaly Detection | — | run_ml.py |
| `ml/train_drilling_efficiency.py` | ML Model 2 — Drilling Efficiency | — | run_ml.py |
| `ml/train_pressure_prediction.py` | ML Model 1 — Pressure Prediction | — | run_ml.py |
| `ml/training/HOW_IT_WORKS.txt` | — | — | — |
| `ml/training/MLFLOW_SETUP.txt` | — | — | — |

## Snowflake serving layer

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `snowflake/create_views.py` | Phase 8 — Snowflake Serving Layer | — | run_snowflake.py |
| `snowflake/load_snowflake.py` | Phase 8 — Snowflake Serving Layer | — | run_snowflake.py |
| `snowflake/requirements.txt` | — | — | — |
| `snowflake/run_snowflake.py` | Phase 8 — Snowflake Serving Layer | create_views.py, load_snowflake.py, setup_snowflake.py | — |
| `snowflake/setup_mcp.sql` | ============================================================ | — | — |
| `snowflake/setup_snowflake.py` | Phase 8 — Snowflake Serving Layer | — | run_snowflake.py |

## Airflow DAGs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `airflow/dags/HOW_IT_WORKS.txt` | — | — | — |
| `airflow/dags/operators/__init__.py` | (no module docstring) | — | — |
| `airflow/dags/operators/databricks_sql_operator.py` | Custom Airflow operators for the Volve pipeline. | — | — |
| `airflow/dags/volve_daily_pipeline.py` | Volve Daily Pipeline DAG | — | — |

## Confluence sync pages

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `confluence/00_START_HERE.md` | Start Here — Volve Sensor & Production Analytics Pipeline | — | — |

## Great Expectations / data quality

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `data_quality/HOW_IT_WORKS.txt` | — | — | — |

## Tests / contracts

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `tests/HOW_IT_WORKS.txt` | — | — | — |
| `tests/boundary_contract.py` | Stack + scope boundary contract — deterministic gate over this repo's locked stack. | — | — |
| `tests/doc_reference_contract.py` | Doc-reference contract — deterministic gate against documentation drift. | — | — |
| `tests/identity_contract.py` | Identity contract — deterministic gate over the (well_id, DATEPRD) / (well_id, md_m) grain. | — | — |

## Learning

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `learning/CURRICULUM.md` | Learning Curriculum — Volve Sensor & Production Analytics Pipeline | — | — |
| `learning/LEARNING_LOG.md` | Learning Log — Volve Sensor & Production Analytics Pipeline | — | — |

## Simulation lab

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `simulation/ISOLATION_CONTRACT.md` | Isolation Contract — Volve Simulation Lab | — | — |
| `simulation/check_isolation.py` | Isolation guard for the Volve simulation lab (simulation/). | — | — |
| `simulation/faults/README.md` | Fault Catalog — Volve Simulation Lab | — | — |
| `simulation/faults/catalog/F01.md` | F01 | — | — |
| `simulation/faults/catalog/F02.md` | F02 | — | — |
| `simulation/faults/catalog/F03.md` | F03 | — | — |
| `simulation/faults/catalog/F04.md` | F04 | — | — |
| `simulation/faults/inject.py` | Inject a named, reversible fault into the SIM lab only (never touches real models). | — | — |
| `simulation/faults/reset.py` | Reset the SIM lab to clean baseline — re-seed + re-build sim only. Never hand-patched. | — | — |
| `simulation/specs/01_SIM_silver_dedup_troubleshoot.md` | SIM-01: Troubleshoot — Silver production dedup grain break | — | — |
| `simulation/specs/02_SIM_trajectory_explode_migration.md` | SIM-02: Migration drill — trajectory explode logic | — | — |
| `simulation/specs/03_SIM_snowflake_load_optimize.md` | SIM-03: Optimization drill — Snowflake truncate+reload vs incremental | — | — |
| `simulation/specs/04_SIM_well_scope_value_reconciliation.md` | SIM-04: Value-reconciliation drill — 3-well scope leak | — | — |

## Scripts

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `scripts/gen_repo_map.py` | Repo-map generator — the NAVIGATION half of the ANTI-SHORTCUT PROTOCOL (see CLAUDE.md). | — | — |
| `scripts/sync_docs_to_confluence.py` | Publish this repo's real docs/ set to Confluence as living documentation. | — | — |

## Config

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `airflow/MWAA_SETUP.txt` | — | — | — |
| `airflow/requirements.txt` | — | — | — |
| `infrastructure/docker-compose.yml` | — | — | — |

## Other

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `ingestion/nifi/DASHBOARD_SETUP.txt` | — | — | — |
| `ingestion/nifi/HOW_IT_WORKS.txt` | — | — | — |
