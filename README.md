# Volve Sensor & Production Analytics Pipeline

An end-to-end data engineering pipeline built on the **Equinor Volve open dataset** — a real North Sea oil field dataset released publicly by Equinor (Norway). This project demonstrates production-grade data engineering covering lakehouse ingestion, multi-layer transformation, data quality, ML, and orchestration.

---

## Project Overview

The Volve field operated from 2007 to 2016 in the Norwegian North Sea. Equinor released the full dataset in 2018 as an open dataset for research and learning. This pipeline processes raw sensor and production data from 3 wells (F-1, F-11, F-12), transforms it through Bronze → Silver → Gold layers using the Databricks Lakehouse, trains ML models via MLflow, and serves insights through Snowflake.

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
  ┌──────────┐    ┌──────────────┐
  │Snowflake │    │   MLflow     │  ← 3 models: pressure, efficiency, anomaly
  │(Serving) │    │(Databricks)  │
  └──────────┘    └──────────────┘

  Orchestrated end-to-end by Apache Airflow (10-task DAG)
```

---

## Tech Stack

| Layer | Tool | Notes |
|-------|------|-------|
| Data Source | Equinor Volve Data Village | Databricks Volume (Delta Share) |
| Bronze / Silver / Gold | Databricks SQL Warehouse | Serverless, Unity Catalog |
| Table Format | Delta Lake | ACID, time travel, schema evolution |
| Orchestration | Apache Airflow (Docker) | 10-task DAG |
| Data Quality | Great Expectations | DQ gates between layers |
| Serving | Snowflake | Reporting views for BI |
| ML Tracking | MLflow (Databricks) | Experiment logging, model registry |
| Scripting | Python + databricks-sql-connector | Run from GitHub Codespaces |
| Dev Environment | GitHub Codespaces | 2 cores, 8GB RAM |

---

## Data Sources

| Source | Format | Volume | Description |
|--------|--------|--------|-------------|
| Production Data | Excel (.xlsx) | 1 file, ~4,967 records | Daily oil/gas/water volumes per well, 2007–2016 |
| WITSML Trajectory | XML | 11 trajectory files (3 wells) | Wellbore survey stations — measured depth, inclination, azimuth |
| WITSML Sensor Logs | XML | 11,664 files (sampled) | Downhole pressure, temperature, torque, ROP |
| Well Logs | LAS | 301 files | Petrophysical measurements per depth |

> **Wells in scope:** F-1, F-11, F-12 (free-tier constraint — 3 wells from 29 available)

---

## Pipeline Layers

### Bronze — Raw Landing
- Source: Databricks Volume `/Volumes/equinor_asa_volve_data_village/public/volve/`
- `read_files()` via SQL Warehouse — Excel and WITSML XML supported
- No transformation — raw data preserved as-is
- Metadata added: `ingestion_ts`, `source_system`, `source_file`, `well_id`
- Tables: `claudecatalog.bronze.raw_production`, `claudecatalog.bronze.raw_witsml_trajectory`

### Silver — Cleaned & Validated
- Type casting, NULL handling, deduplication
- Derived columns: `water_cut_pct = BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100`
- Derived columns: `gas_oil_ratio = BORE_GAS_VOL / BORE_OIL_VOL`
- Trajectory: explode `trajectory_stations_json` → one row per survey station
- DQ gate (Great Expectations) — blocks Gold if pass rate < 95%
- Tables: `claudecatalog.silver.cleaned_production`, `claudecatalog.silver.cleaned_trajectory`

### Gold — KPIs & Feature Store
- Production KPIs aggregated by well + date
- Anomaly flags: pressure spikes, zero-production uptime, water cut spikes, GOR anomalies
- ML feature store for model training
- Tables: `claudecatalog.gold.production_kpis`, `claudecatalog.gold.ml_feature_store`

---

## ML Models

| Model | Algorithm | Target | Framework |
|-------|-----------|--------|-----------|
| `volve_pressure_prediction` | XGBoost Regressor | Next-day downhole pressure | MLflow |
| `volve_drilling_efficiency` | Random Forest Regressor | ROP efficiency score | MLflow |
| `volve_anomaly_detection` | Isolation Forest | is_anomaly (binary) | MLflow |

---

## Airflow DAG — 10 Tasks

```
check_source_files
    ├── run_bronze_production ──────┐
    └── run_bronze_witsml ──────────┤
                                   ├── run_silver_production ──┐
                                   └── run_silver_trajectory ──┤
                                                               └── check_dq_silver  ← GATE
                                                                       ├── run_gold_production ──┐
                                                                       └── run_gold_features ────┤
                                                                                                 └── run_ml_scoring
                                                                                                          └── send_daily_report
```

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
- `is_water_cut_spike`: water cut > 80% when lag was < 60%
- `is_gor_anomaly`: GOR > 3× well baseline

---

## Repository Structure

```
├── bronze/
│   ├── bronze_production.py       # Excel → claudecatalog.bronze.raw_production
│   ├── bronze_witsml.py           # WITSML XML → claudecatalog.bronze.raw_witsml_trajectory
│   └── run_bronze.py              # Orchestrator — runs both in sequence
│
├── silver/                        # Silver layer scripts (in progress)
├── gold/                          # Gold layer scripts (planned)
├── ml/                            # MLflow training + scoring (planned)
├── data_quality/                  # Great Expectations suites (planned)
├── airflow/                       # Airflow DAG definitions (planned)
├── tests/                         # Unit + integration tests (planned)
├── infrastructure/                # Setup guides, Terraform
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
- Python 3.10+ with `databricks-sql-connector`, `python-dotenv`
- Snowflake account (for serving layer)
- Docker (for Airflow orchestration)

### Quick Start

```bash
# Clone
git clone https://github.com/rajeluqman/Volve-Sensor-Production-Analytics-Pipeline.git
cd Volve-Sensor-Production-Analytics-Pipeline

# Configure credentials
cp .env.example .env
# Edit .env — add Databricks host, token, SQL Warehouse ID

# Install dependencies
pip install databricks-sql-connector python-dotenv

# Run Bronze layer
python bronze/run_bronze.py
```

### Running Individual Layers

```bash
# Bronze — production data only
python bronze/bronze_production.py

# Bronze — WITSML trajectory data only
python bronze/bronze_witsml.py

# Bronze — both (sequential)
python bronze/run_bronze.py
```

---

## Build Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Documentation & Repository Setup | Done |
| Phase 1 | Infrastructure Setup (Databricks, AWS, Snowflake) | Done |
| Phase 2 | Bronze Layer | **Done** |
| Phase 3 | Silver Layer | Next |
| Phase 4 | Gold Layer + Feature Store | Planned |
| Phase 5 | ML Models (MLflow) | Planned |
| Phase 6 | Orchestration (Airflow DAG) | Planned |
| Phase 7 | Data Quality (Great Expectations) | Planned |
| Phase 8 | Serving Layer (Snowflake) | Planned |
| Phase 9 | Testing + Documentation | Planned |

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
| Docker Airflow vs MWAA | $0 vs ~$50/month — code-identical to MWAA, valid portfolio demonstration |
| Sequential execution | 8GB Codespaces RAM — NiFi and Airflow cannot run concurrently |
