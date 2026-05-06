# Volve Sensor & Production Analytics Pipeline

An end-to-end data engineering pipeline built on the **Equinor Volve open dataset** — a real North Sea oil field dataset released publicly by Equinor (Norway). This project demonstrates production-grade data engineering covering lakehouse ingestion, multi-layer transformation, data quality, ML, and orchestration.

---

## Project Overview

The Volve field operated from 2007 to 2016 in the Norwegian North Sea. Equinor released the full dataset in 2018 as an open dataset for research and learning. This pipeline processes raw sensor and production data from 3 wells (F-1, F-11, F-12), transforms it through Bronze → Silver → Gold layers using the Databricks Lakehouse, trains ML models via MLflow, orchestrates via Airflow, validates via Great Expectations, and serves insights through Snowflake BI views.

**Use case:** Detect production anomalies, predict downhole pressure, and score drilling efficiency — the kind of analytics an O&G data engineering team would run in production.

---

## Architecture

```
Equinor Volve Data Village
(Databricks Volume — Delta Share)
         │
         ▼
  ┌─────────────────────────────┐
  │   Bronze Layer              │  ← Raw ingest via Databricks SQL Warehouse
  │   claudecatalog.bronze.*    │    read_files() from Volume (Excel + WITSML XML)
  └─────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────┐
  │   Silver Layer              │  ← Clean, cast, dedupe, derived columns
  │   claudecatalog.silver.*    │    DQ gate: Great Expectations (> 95% pass)
  └─────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────┐
  │   Gold Layer                │  ← KPIs, anomaly flags, ML feature store
  │   claudecatalog.gold.*      │
  └─────────────────────────────┘
         │               │
         ▼               ▼
  ┌──────────────┐  ┌──────────────┐
  │  Snowflake   │  │   MLflow     │  ← 3 models: pressure, efficiency, anomaly
  │  VOLVE_DB    │  │ (Databricks) │
  │  5 BI views  │  └──────────────┘
  └──────────────┘

  Orchestrated end-to-end by Apache Airflow (10-task DAG, Docker)
```

---

## Tech Stack

| Layer | Tool | Notes |
|-------|------|-------|
| Data Source | Equinor Volve Data Village | Databricks Volume (Delta Share) |
| Bronze / Silver / Gold | Databricks SQL Warehouse | Serverless, Unity Catalog |
| Table Format | Delta Lake | ACID, time travel, schema evolution |
| Orchestration | Apache Airflow (Docker) | 10-task DAG, LocalExecutor |
| Data Quality | Great Expectations | SQL-based DQ gates between layers |
| Serving | Snowflake | 5 BI reporting views in VOLVE_DB.SERVING |
| ML Tracking | MLflow (Databricks) | Experiment logging, model registry |
| Scripting | Python + databricks-sql-connector | Run from GitHub Codespaces |
| Dev Environment | GitHub Codespaces | 2 cores, 8GB RAM |

---

## Data Sources

| Source | Format | Volume | Description |
|--------|--------|--------|-------------|
| Production Data | Excel (.xlsx) | 1 file, 4,967 records | Daily oil/gas/water volumes per well, 2007–2016 |
| WITSML Trajectory | XML | 11 files (3 wells) | Wellbore survey stations — measured depth, inclination, azimuth |
| WITSML Sensor Logs | XML | 11,664 files (sampled) | Downhole pressure, temperature, torque, ROP |
| Well Logs | LAS | 301 files | Petrophysical measurements per depth |

> **Wells in scope:** F-1, F-11, F-12 (free-tier constraint — 3 wells from 29 available)

---

## Pipeline Layers

### Bronze — Raw Landing
- Source: Databricks Volume `/Volumes/equinor_asa_volve_data_village/public/volve/`
- `read_files()` via SQL Warehouse — Excel and WITSML XML supported natively
- No transformation — raw data preserved as-is with metadata columns
- Metadata added: `ingestion_ts`, `source_system`, `source_file`, `well_id`
- Tables: `claudecatalog.bronze.raw_production`, `claudecatalog.bronze.raw_witsml_trajectory`

### Silver — Cleaned & Validated
- Type casting (TRY_CAST all numerics → DOUBLE), NULL handling, deduplication
- Derived: `water_cut_pct = BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100`
- Derived: `gas_oil_ratio = BORE_GAS_VOL / BORE_OIL_VOL`
- Trajectory: explode `trajectory_stations_json` → one row per survey station
- Flags: `is_zero_prod_uptime`, `is_pressure_valid`, `is_md_valid`, `is_incl_valid`
- Tables: `claudecatalog.silver.cleaned_production`, `claudecatalog.silver.cleaned_trajectory`

### Gold — KPIs & Feature Store
- Anomaly flags: pressure spikes, zero-production uptime, water cut spikes, GOR anomalies
- Rolling averages: 7-day and 30-day for oil volume, gas volume, water cut, pressure
- Monthly cumulative volumes, `pressure_delta_24h`
- ML feature store: lag features (1/2/3/7d), rolling stats, trajectory well characteristics
- Three ML targets: `next_day_pressure`, `rop_efficiency_score`, `is_anomaly`
- Tables: `claudecatalog.gold.production_daily`, `claudecatalog.gold.ml_feature_store`

### Serving — Snowflake BI Views
- Staging tables: `VOLVE_DB.SERVING.production_daily`, `VOLVE_DB.SERVING.ml_predictions`
- 4,967 rows loaded from Databricks Gold via Python connector

| View | Description |
|------|-------------|
| `vw_daily_production_kpis` | Ops KPIs per well/date — volumes, pressure, rolling averages |
| `vw_anomaly_alerts` | Anomaly flags with severity (CRITICAL / HIGH / MEDIUM), filtered to anomaly days only |
| `vw_production_trends` | Monthly aggregates per well — total volumes, avg pressure, anomaly days |
| `vw_ml_predictions` | ML actual vs predicted pressure + prediction result labels (TRUE_POS / FALSE_POS) |
| `vw_well_comparison` | Cross-well KPI comparison per year — anomaly %, volumes, pressure |

---

## ML Models

| Model | Algorithm | Target | Framework |
|-------|-----------|--------|-----------|
| `volve_pressure_prediction` | XGBoost Regressor | Next-day downhole pressure | MLflow |
| `volve_drilling_efficiency` | Random Forest Regressor | ROP efficiency score | MLflow |
| `volve_anomaly_detection` | Isolation Forest | is_anomaly (binary) | MLflow |

All models trained locally, logged to Databricks MLflow experiment registry (`claudecatalog.ml.*`).

---

## Airflow DAG — 10 Tasks

```
check_source_files
    ├── run_bronze_production ──────┐
    └── run_bronze_witsml ──────────┤
                                   ├── run_silver_production ──┐
                                   └── run_silver_trajectory ──┤
                                                               └── check_dq_silver  ← GATE (blocks if < 95%)
                                                                       ├── run_gold_production ──┐
                                                                       └── run_gold_features ────┤
                                                                                                 └── run_ml_scoring
                                                                                                          └── send_daily_report
```

Schedule: `0 2 * * *` (daily at 02:00 UTC). DQ gate (Task 6) blocks downstream tasks if Silver pass rate < 95%.

---

## Data Quality Rules

| Suite | Table | Pass Threshold |
|-------|-------|----------------|
| `bronze_production_suite` | `bronze.raw_production` | > 95% |
| `silver_production_suite` | `silver.cleaned_production` | > 95% |
| `silver_trajectory_suite` | `silver.cleaned_trajectory` | > 95% |
| `gold_feature_suite` | `gold.ml_feature_store` | > 95% |

Alert thresholds enforced in Gold:
- `is_anomaly_pressure`: pressure delta 24h > 500 psi
- `is_zero_prod_uptime`: `BORE_OIL_VOL == 0` AND `ON_STREAM_HRS > 0`
- `is_water_cut_spike`: water cut > 80% when prior day was < 60%
- `is_gor_anomaly`: GOR > 3× well baseline

---

## Repository Structure

```
├── bronze/
│   ├── bronze_production.py       # Excel → claudecatalog.bronze.raw_production
│   ├── bronze_witsml.py           # WITSML XML → claudecatalog.bronze.raw_witsml_trajectory
│   └── run_bronze.py              # Orchestrator
│
├── silver/
│   ├── silver_production.py       # bronze.raw_production → silver.cleaned_production
│   ├── silver_trajectory.py       # bronze.raw_witsml_trajectory → silver.cleaned_trajectory
│   └── run_silver.py              # Orchestrator
│
├── gold/
│   ├── gold_production_daily.py   # silver → gold.production_daily (KPIs + anomaly flags)
│   ├── gold_ml_features.py        # silver → gold.ml_feature_store (lag + rolling features)
│   └── run_gold.py                # Orchestrator
│
├── ml/
│   ├── train_pressure_prediction.py   # XGBoost → next_day_pressure
│   ├── train_drilling_efficiency.py   # Random Forest → rop_efficiency_score
│   ├── train_anomaly_detection.py     # Isolation Forest → is_anomaly
│   ├── score_models.py                # Batch inference → gold.ml_predictions
│   └── run_ml.py                      # Orchestrator
│
├── data_quality/
│   ├── suites/
│   │   ├── bronze_production_suite.py  # 8 expectations
│   │   ├── silver_production_suite.py  # 10 expectations
│   │   ├── silver_witsml_suite.py      # 8 expectations
│   │   └── gold_feature_suite.py       # 9 expectations
│   └── run_dq.py                       # Orchestrator → writes results to silver.dq_results
│
├── snowflake/
│   ├── setup_snowflake.py         # Create VOLVE_DB.SERVING + staging tables
│   ├── load_snowflake.py          # ETL Databricks Gold → Snowflake (truncate + reload)
│   ├── create_views.py            # Create 5 BI views
│   ├── run_snowflake.py           # Orchestrator (--only setup|load|views)
│   └── setup_mcp.sql              # Snowflake MCP server DDL (run once in Worksheet)
│
├── airflow/
│   ├── dags/
│   │   ├── volve_daily_pipeline.py          # 10-task DAG (schedule: 0 2 * * *)
│   │   └── operators/
│   │       ├── databricks_sql_operator.py   # DatabricksSQLScriptOperator + QueryOperator
│   │       └── __init__.py
│   └── requirements.txt
│
├── infrastructure/
│   └── docker-compose.yml         # Airflow 2.9.3 + Postgres (LocalExecutor)
│
├── tests/                         # Unit + integration tests
└── docs/
    ├── ARCHITECTURE.md            # Solution architecture + ADRs
    ├── BRD.md                     # Business requirements
    ├── DRD.md                     # Data requirements + schemas
    ├── PIPELINE_SPEC.md           # Transform logic specification
    ├── DQD.md                     # Data quality rules
    └── OPS_RUNBOOK.md             # Operations runbook
```

---

## Getting Started

### Prerequisites

- Databricks workspace with SQL Warehouse (serverless or standard)
- Access to Equinor Volve Data Village (via Delta Share or local copy)
- Snowflake account with `VOLVE_DB` database and `SERVING` schema
- Docker (for Airflow orchestration)
- Python 3.10+

### Quick Start

```bash
# Clone
git clone https://github.com/rajeluqman/Volve-Sensor-Production-Analytics-Pipeline.git
cd Volve-Sensor-Production-Analytics-Pipeline

# Configure credentials
cp .env.example .env
# Edit .env — add Databricks host, token, warehouse ID, Snowflake credentials

# Run Bronze layer
pip install databricks-sql-connector python-dotenv
python bronze/run_bronze.py

# Run Silver layer
python silver/run_silver.py

# Run Gold layer
python gold/run_gold.py

# Train ML models
pip install xgboost scikit-learn mlflow
python ml/run_ml.py

# Run Data Quality
pip install -r data_quality/requirements.txt
python data_quality/run_dq.py

# Load Snowflake serving layer
pip install -r snowflake/requirements.txt
cd snowflake && python run_snowflake.py
```

### Airflow (Docker)

```bash
# Start Airflow
cd infrastructure && docker-compose up -d

# Install pipeline deps inside Airflow container
docker exec infrastructure-airflow-scheduler-1 \
  pip install -r /workspace/airflow/requirements.txt

# DAG will run daily at 02:00 UTC — trigger manually:
# Airflow UI → http://localhost:8080 → volve_daily_pipeline → Trigger DAG
```

---

## Build Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Documentation & Repository Setup | Done |
| Phase 1 | Infrastructure Setup (Databricks, AWS, Snowflake) | Done |
| Phase 2 | Bronze Layer | Done |
| Phase 3 | Silver Layer | Done |
| Phase 4 | Gold Layer + Feature Store | Done |
| Phase 5 | ML Models (MLflow) | Done |
| Phase 6 | Orchestration (Airflow DAG) | Done |
| Phase 7 | Data Quality (Great Expectations) | Done |
| Phase 8 | Serving Layer (Snowflake) | Done |
| Phase 9 | Testing + Documentation Finalisation | In Progress |

---

## Dataset

**Equinor Volve Data Village** — publicly available at [equinor.com/energy/volve-data-sharing](https://www.equinor.com/energy/volve-data-sharing)

Released under the Equinor Open Data Licence. Not included in this repository. Access via Databricks Delta Share (`equinor_asa_volve_data_village` catalog) or download and host in your own cloud storage.

---

## Key Engineering Decisions

| Decision | Rationale |
|----------|-----------|
| Databricks SQL Warehouse (serverless) | Data already in Databricks Volume — no Glue/Spark cluster needed |
| `read_files()` for ingestion | Native Databricks SQL function — handles Excel + XML without custom ETL code |
| `TO_JSON(trajectoryStation)` in Bronze | WITSML XML schema varies across wellbores — JSON string avoids UNION ALL conflict |
| 3 wells only (F-1, F-11, F-12) | Free-tier SQL Warehouse constraint — representative sample of 29 wells |
| Docker Airflow vs MWAA | $0 vs ~$50/month — code-identical to MWAA |
| Sequential execution (NiFi / Airflow) | 8GB Codespaces RAM — cannot run concurrent Docker services |
| Python connector for Snowflake load | Direct ETL via pandas + snowflake-connector — no intermediate S3 staging needed |
