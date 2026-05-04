# Volve Sensor & Production Analytics Pipeline

An end-to-end data engineering pipeline built on the **Equinor Volve open dataset** — a real North Sea oil field dataset released publicly by Equinor (Norway). This project demonstrates production-grade data engineering covering ingestion, transformation, data quality, ML, and orchestration.

---

## Project Overview

The Volve field operated from 2007 to 2016 in the Norwegian North Sea. Equinor released the full dataset in 2018 as an open dataset for research and learning. This pipeline ingests raw sensor and production data from 3 wells (F-1, F-11, F-12), transforms it through Bronze → Silver → Gold layers, trains ML models, and serves insights via Snowflake.

**Use case:** Detect production anomalies, predict downhole pressure, and score drilling efficiency — the kind of analytics an O&G data team would run in production.

---

## Architecture

```
Raw Data (S3 Landing)
        │
        ▼
  [Apache NiFi]          ← Ingestion: Excel, WITSML XML, LAS files
        │
        ▼
  Bronze Layer           ← Raw data as-is + metadata tags (AWS Glue / PySpark)
        │
        ▼
  Silver Layer           ← Cleaned, validated, derived columns (Databricks)
        │
        ▼
   Gold Layer            ← KPIs, aggregates, ML feature store (Databricks)
        │
        ▼
  Snowflake Views        ← BI-ready serving layer
        │
        ▼
   ML Models             ← XGBoost, Random Forest, Isolation Forest (MLflow)
```

**Orchestrated end-to-end by Apache Airflow (10-task DAG)**

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Ingestion | Apache NiFi + Groovy scripting |
| Cloud Storage | AWS S3 + Delta Lake |
| Bronze Transform | AWS Glue (PySpark) |
| Silver / Gold | Databricks (Runtime 14.x ML) |
| Orchestration | Apache Airflow |
| Data Quality | Great Expectations |
| Serving / Warehouse | Snowflake |
| ML Tracking | MLflow (built into Databricks) |
| Dev Environment | GitHub Codespaces |

---

## Data Sources

| Source | Format | Volume | Description |
|--------|--------|--------|-------------|
| Production Data | Excel (.xlsx) | Daily production per well | Oil, gas, water volumes, uptime |
| WITSML Sensor Logs | XML | ~11,664 files | Downhole pressure, temperature, torque |
| Well Logs | LAS | 301 files | Petrophysical measurements per depth |

---

## Pipeline Layers

### Bronze
- Raw ingest from S3 landing zone
- No transformation — preserves source fidelity
- Adds metadata: `ingestion_ts`, `source_system`, `source_file`
- Targets: `bronze.raw_production`, `bronze.witsml_*`, `bronze.raw_well_logs`

### Silver
- Deduplication, type casting, NULL handling
- Derived columns: `water_cut_pct`, `gas_oil_ratio`, `well_id`
- Data quality gate — blocks downstream if DQ fails
- Targets: `silver.cleaned_production`, `silver.cleaned_trajectory`

### Gold
- KPI aggregation by well and date
- Anomaly flags: pressure spikes, zero-production uptime, water cut spikes, GOR anomalies
- ML feature store for model training
- Target: `gold.production_kpis`, `gold.ml_feature_store`

---

## ML Models

| Model | Algorithm | Target |
|-------|-----------|--------|
| Pressure Prediction | XGBoost Regressor | Next-day downhole pressure |
| Drilling Efficiency | Random Forest Regressor | ROP efficiency score |
| Anomaly Detection | Isolation Forest | Is anomaly (binary) |

All models tracked via MLflow with experiment logging, parameter tracking, and model registry.

---

## Airflow DAG — 10 Tasks

```
check_source_files
    ├── run_glue_bronze_production ──┐
    └── run_glue_bronze_witsml ─────┤
                                    ├── run_silver_production ──┐
                                    └── run_silver_witsml ──────┤
                                                                ├── check_dq_silver  ← GATE
                                                                    ├── run_gold_production ──┐
                                                                    └── run_gold_features ────┤
                                                                                             └── run_ml_scoring
                                                                                                      └── send_daily_report
```

---

## Data Quality Rules

| Suite | Table | Pass Threshold |
|-------|-------|---------------|
| bronze_production_suite | bronze.raw_production | > 95% |
| silver_production_suite | silver.cleaned_production | > 95% |
| silver_witsml_suite | silver.cleaned_trajectory | > 95% |
| gold_feature_suite | gold.ml_feature_store | > 95% |

---

## Repository Structure

```
├── ingestion/          # NiFi templates + Groovy processor scripts
├── bronze/             # AWS Glue jobs (PySpark)
├── silver/             # Databricks notebooks — clean & validate
├── gold/               # Databricks notebooks — KPIs & feature store
├── ml/                 # MLflow training scripts + scoring
├── data_quality/       # Great Expectations suites + checkpoints
├── airflow/            # DAG definitions
├── tests/              # Unit + integration tests
├── infrastructure/     # Terraform + credentials setup guide
├── docs/               # BRD, DRD, architecture, pipeline spec, runbooks
└── setup.sh            # Environment bootstrap script
```

---

## Getting Started

### Prerequisites

- AWS account (S3, Glue)
- Databricks workspace (trial or paid)
- Snowflake account (trial)
- Docker (for NiFi and Airflow)
- GitHub Codespaces or local environment with 8GB+ RAM

### Setup

```bash
# Clone the repo
git clone https://github.com/rajeluqman/Volve-Sensor-Production-Analytics-Pipeline.git
cd Volve-Sensor-Production-Analytics-Pipeline

# Copy env template and fill in credentials
cp .env.example .env

# Run environment bootstrap
chmod +x setup.sh && ./setup.sh
```

Then follow `infrastructure/credentials/SETUP_GUIDE.txt` to authenticate AWS, Databricks, and Snowflake.

---

## Dataset

**Equinor Volve Data Village** — publicly available at [equinor.com/energy/volve-data-sharing](https://www.equinor.com/energy/volve-data-sharing)

Released under the Equinor Open Data Licence. Not included in this repository — download separately and place in S3 landing bucket.

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Documentation & Repository Setup | Done |
| Phase 1 | Infrastructure Setup | In Progress |
| Phase 2–9 | Pipeline Build-out | Planned |
