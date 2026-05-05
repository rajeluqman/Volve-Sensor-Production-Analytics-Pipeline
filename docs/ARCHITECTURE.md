# ARCHITECTURE.md — Solution Architecture
## Volve Sensor & Production Analytics Pipeline

**Version:** 2.0 | **Last Updated:** 2026-05-05

> Version 2.0 reflects architecture revision made during Phase 1 — original NiFi + S3 + Glue ingestion replaced with direct Databricks Volume access via Delta Share.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│          Equinor Volve Data Village                     │
│   (Databricks Delta Share — read-only public catalog)   │
│   Catalog: equinor_asa_volve_data_village               │
│   Path: /Volumes/.../volve/                             │
└─────────────────────────────────────────────────────────┘
                          │
                          │ read_files() via SQL Warehouse
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   BRONZE LAYER                          │
│   claudecatalog.bronze.raw_production                   │
│   claudecatalog.bronze.raw_witsml_trajectory            │
│   — Raw data as-is + ingestion_ts, source_system tags   │
│   — Partitioned by well_id (+ date_year for production) │
└─────────────────────────────────────────────────────────┘
                          │
                          │ SQL Warehouse CTAS
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   SILVER LAYER                          │
│   claudecatalog.silver.cleaned_production               │
│   claudecatalog.silver.cleaned_trajectory               │
│   — Type cast, NULL handling, deduplication             │
│   — Derived: water_cut_pct, gas_oil_ratio, well_id      │
│   — DQ Gate (Great Expectations > 95%) blocks Gold      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    GOLD LAYER                           │
│   claudecatalog.gold.production_kpis                    │
│   claudecatalog.gold.ml_feature_store                   │
│   — KPIs per well per date                              │
│   — Anomaly flags (pressure, GOR, water cut, uptime)    │
│   — Features for ML model training                      │
└─────────────────────────────────────────────────────────┘
              │                        │
              ▼                        ▼
┌─────────────────┐         ┌─────────────────────────┐
│    Snowflake    │         │     MLflow (Databricks) │
│  Serving Layer  │         │  3 models tracked +     │
│  BI views for   │         │  registered in catalog  │
│  dashboards     │         └─────────────────────────┘
└─────────────────┘

           Orchestrated by Apache Airflow (10-task DAG)
           Quality gated by Great Expectations suites
```

---

## 2. Layer Responsibilities

| Layer | Compute | Responsibility |
|-------|---------|----------------|
| Bronze | Databricks SQL Warehouse | Raw ingest from Volume via `read_files()` + metadata tags |
| Silver | Databricks SQL Warehouse | Clean, cast, dedupe, validate, derived columns |
| Gold | Databricks SQL Warehouse | KPIs, feature store, anomaly flags |
| Serving | Snowflake (X-Small) | Reporting views for BI consumption |
| Orchestration | Airflow (Docker) | 10-task DAG with DQ gate |
| DQ | Great Expectations | Validation suites between layers |
| ML | MLflow (Databricks) | Experiment tracking, model versioning, scoring |

---

## 3. Compute Strategy

**Single compute engine: Databricks SQL Warehouse (Serverless Starter)**

| Item | Detail |
|------|--------|
| Warehouse ID | `470a6646b4bd0dd2` |
| Type | Serverless Starter (Small) |
| Auto-stop | 10 min inactivity |
| Catalog | `claudecatalog` (Unity Catalog) |
| No classic cluster | Confirmed — all SQL, no PySpark clusters |

Scripts run from GitHub Codespaces using `databricks-sql-connector`. No local compute required for ETL.

---

## 4. Data Flow

### Production Data (Excel → Bronze → Silver → Gold)

```
Volume: .../Production_data/Volve production data.xlsx
    │
    │ read_files(format='excel')  — columns as _c0.._c23 (header not auto-detected)
    ▼
bronze.raw_production
    │ 4,967 rows · F-1 (2014-2016), F-11 (2013-2016), F-12 (2008-2016)
    │ Partitioned: date_year + well_id
    ▼
silver.cleaned_production
    │ Typed: DATEPRD→DATE, volumes→DOUBLE
    │ Derived: water_cut_pct, gas_oil_ratio, well_id (clean regex)
    │ DQ validated
    ▼
gold.production_kpis + gold.ml_feature_store
```

### WITSML Data (XML → Bronze → Silver)

```
Volume: .../WITSML Realtime drilling data/
  well_folder/N/trajectory/*.xml
    │
    │ Discover: LIST Volume → filter F-1|F-11|F-12 → find trajectory/ subdirs
    │ read_files(format='xml', rowTag='trajectory')
    │ TO_JSON(trajectoryStation) — serialise nested struct (schema varies by WITSML version)
    ▼
bronze.raw_witsml_trajectory
    │ 22 trajectories · mandatory WITSML fields + stations as JSON string
    │ Partitioned: well_id
    ▼
silver.cleaned_trajectory
    │ Parse trajectory_stations_json → explode → one row per survey station
    │ Columns: md_m, incl_deg, azi_deg, tvd_m, disp_ns_m, disp_ew_m
```

---

## 5. Infrastructure

| Resource | Spec | Cost Model |
|----------|------|------------|
| GitHub Codespaces | 2 cores, 8GB RAM, 32GB storage | Free tier |
| Databricks | Serverless SQL Warehouse | $400 trial credit |
| AWS S3 | 3 buckets (landing, bronze, silver) | ~$1–5/month |
| Snowflake | X-Small warehouse | 30-day trial |

### Codespaces RAM Allocation (Sequential Execution)

| Mode | Active Services | RAM Used |
|------|----------------|----------|
| Transform | Scripts only (no Docker) | ~2 GB |
| Orchestrate | Airflow Docker (Airflow OFF when not needed) | ~3.5 GB |
| Ingestion | NiFi Docker (if used) | ~4 GB |

> **Rule:** Airflow and NiFi must not run concurrently — 8GB RAM insufficient for both.

---

## 6. Architecture Decision Records

### ADR-001: Skip NiFi + AWS Glue ingestion
**Decision:** Databricks Volume direct access replaces NiFi → S3 → Glue path.

**Why:** Equinor Volve dataset is available as a Databricks Delta Share (`equinor_asa_volve_data_village` catalog). Data is already in a Databricks Volume, accessible via `read_files()` in SQL Warehouse. Building NiFi + Glue would add operational complexity with no data movement benefit.

**Trade-off:** Reduces portfolio breadth (no NiFi demo), but produces a cleaner, more realistic Databricks-native architecture.

---

### ADR-002: SQL Warehouse only — no classic cluster
**Decision:** All ETL runs on SQL Warehouse. No classic compute clusters provisioned.

**Why:** Classic clusters consume $400 trial credit quickly (~$0.15–0.40/DBU). SQL Warehouse Serverless is more cost-efficient for SQL workloads and sufficient for this dataset size.

**Implication:** PySpark API not available — all transforms written as SQL DDL/DML executed via `databricks-sql-connector` from Codespaces.

---

### ADR-003: TO_JSON() for WITSML nested structs
**Decision:** `trajectoryStation` column stored as JSON string, not native struct.

**Why:** WITSML XML schema varies between wellbore files (WITSML 1.3.1 vs 1.4.1 have different optional fields). A UNION ALL across multiple trajectory files fails with `INCOMPATIBLE_COLUMN_TYPE` when struct schemas differ. Serialising to JSON avoids the conflict at Bronze layer; Silver parses the JSON into flat columns.

---

### ADR-004: Delta Lake as table format
**Decision:** All layers use Delta tables (Unity Catalog managed).

**Why:** ACID transactions, time travel (data rollback), schema evolution, MERGE operations. Delta is the Databricks-native format and deeply integrated with Unity Catalog governance.

---

### ADR-005: 3 wells only (F-1, F-11, F-12)
**Decision:** Process only F-1, F-11, F-12 from the 29 available wells.

**Why:** Free-tier SQL Warehouse credit constraint. Full 29-well processing estimated at 10× the DBU cost. 3 wells provide sufficient variety (different operators, different production periods) for meaningful analytics and ML.

---

### ADR-006: Docker Airflow instead of MWAA
**Decision:** Apache Airflow running in Docker on Codespaces.

**Why:** Amazon MWAA costs ~$50/month minimum. Docker Airflow is free, uses identical DAG code, and is sufficient for portfolio demonstration. The DAG structure and task definitions are directly portable to MWAA or any managed Airflow provider.

---

### ADR-007: Excel header row workaround
**Decision:** Hardcode column aliases (_c0 → DATEPRD, _c1 → WELL_BORE_CODE, etc.) and filter header row with `WHERE _c0 != 'DATEPRD'`.

**Why:** Databricks SQL Warehouse `read_files(format='excel')` does not automatically detect the header row — all columns are returned as `_c0`, `_c1`, etc. The first data row contains the actual column names. This workaround correctly handles the 24-column production Excel file.

---

## 7. Security

| Layer | Method |
|-------|--------|
| AWS credentials | IAM user `mang-dev` + keys in `.env` (gitignored) |
| Databricks | Personal Access Token in `.env` |
| Databricks secrets | Scope `aws` — access-key + secret-key stored in Databricks Secrets |
| Snowflake | Username + password in `.env` |
| Airflow | Fernet key in `.env`, admin user configured |
| Git | `.env` gitignored, `.env.example` committed (no credentials) |

---

## 8. Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Python scripts | snake_case | `silver_production.py` |
| Delta tables | `layer.table_name` | `silver.cleaned_production` |
| Columns (source) | UPPERCASE (preserved) | `BORE_OIL_VOL` |
| Columns (derived) | snake_case | `water_cut_pct` |
| Well ID | `F-{number}` | `F-1`, `F-11`, `F-12` |
| Partitions | `date_year`, `well_id` | Consistent across all layers |
| DAG ID | `volve_*` | `volve_daily_pipeline` |
| GE suites | `{layer}_{table}_suite` | `silver_production_suite` |

---

*Document Owner: Data Engineering — Volve Pipeline Project*
