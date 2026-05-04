#!/bin/bash

# ============================================================
# setup.sh — Volve Sensor & Production Analytics Pipeline
# Run sekali je: bash setup.sh
# Dia akan create semua folders + files dengan content sekali
# ============================================================

set -e  # Stop kalau ada error

echo "============================================================"
echo " Volve Pipeline — Project Setup"
echo "============================================================"

# ────────────────────────────────────────────────────────────
# STEP 1: Create folder structure
# ────────────────────────────────────────────────────────────
echo ""
echo "[1/5] Creating folder structure..."

mkdir -p docs/ADR
mkdir -p infrastructure/credentials
mkdir -p infrastructure/terraform
mkdir -p ingestion/nifi/templates
mkdir -p ingestion/nifi/scripts
mkdir -p bronze/glue_jobs
mkdir -p silver/notebooks
mkdir -p gold/notebooks
mkdir -p ml/training
mkdir -p ml/scoring
mkdir -p data_quality/expectations
mkdir -p data_quality/checkpoints
mkdir -p airflow/dags
mkdir -p tests/unit
mkdir -p tests/integration

echo "    ✅ Folders created"

# ────────────────────────────────────────────────────────────
# STEP 2: Write all documentation files
# ────────────────────────────────────────────────────────────
echo ""
echo "[2/5] Writing documentation files..."

# ── CLAUDE.md ──────────────────────────────────────────────
cat > CLAUDE.md << 'EOF'
# CLAUDE.md — AI Context File
## Volve Sensor & Production Analytics Pipeline

> ⭐ Claude Code membaca file ini automatik setiap sesi baru.
> Update PROJECT_STATUS.md setiap kali stop kerja.

---

## Project Context

**Project:** Oil & Gas Data Engineering Pipeline — Equinor Volve Field
**Purpose:** Portfolio project — demonstrate end-to-end data engineering skills
**Dataset:** Equinor Volve open dataset (North Sea, Norway)
**Wells in scope:** F-1, F-11, F-12 (3 wells only — free tier constraint)

**Documentation:**
- Business requirements → `docs/BRD.md`
- Data sources & schemas → `docs/DRD.md`
- Architecture decisions → `docs/ARCHITECTURE.md`
- Transform logic → `docs/PIPELINE_SPEC.md`
- Data quality rules → `docs/DQD.md`
- Operations guide → `docs/OPS_RUNBOOK.md`
- MCP setup → `docs/MCP_SETUP.md`

---

## Current Status

→ **Lihat `PROJECT_STATUS.md` untuk progress terkini**

---

## Tech Stack

| Layer | Tool | Version |
|-------|------|---------|
| Ingestion | Apache NiFi + Groovy | 1.23 (Docker) |
| Storage | AWS S3 + Delta Lake | Latest |
| Bronze Transform | AWS Glue | PySpark |
| Silver/Gold | Databricks | $400 trial, Runtime 14.x ML |
| Orchestration | Apache Airflow | Docker, 2.x |
| Data Quality | Great Expectations | Latest |
| Warehouse | Snowflake | 30-day trial |
| ML Tracking | MLflow | Built into Databricks |
| Version Control | Git / GitHub | main branch |
| Dev Environment | GitHub Codespaces | 2 core, 8GB RAM, 32GB storage |

---

## Infrastructure Constraints

```
Codespaces RAM: 8GB total
  NiFi Docker:    ~2.5GB
  Airflow Docker: ~1.5GB
  Overhead:       ~1GB

RULE: Jangan run NiFi + Airflow serentak — sequential execution only

Mode 1 (Ingestion):   NiFi ON,   Airflow OFF
Mode 2 (Orchestrate): Airflow ON, NiFi OFF
Mode 3 (Transform):   Both OFF,  Python scripts + Databricks CLI only
```

---

## Layer Responsibilities

```
Bronze:  Raw data as-is + metadata tags (ingestion_ts, source_system)
Silver:  Clean, dedupe, type cast, NULL handle, validate, derived columns
Gold:    Aggregate, KPI calc, feature engineering, ML feature store
Serving: Snowflake reporting views for BI consumption
```

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Python files | snake_case | `silver_clean_production.py` |
| Tables | `layer.table_name` | `silver.cleaned_production` |
| Columns (new) | snake_case | `water_cut_pct` |
| Columns (source) | UPPERCASE (preserve original) | `BORE_OIL_VOL` |
| Well ID | `F-{number}` | `F-1`, `F-11`, `F-12` |
| Partitions | `date_year`, `well_id` | Standard across all layers |
| DAG ID | `volve_*` | `volve_daily_pipeline` |
| GE suites | `{layer}_{table}_suite` | `silver_production_suite` |

---

## Data Sources

| Source | Format | S3 Path | Bronze Table |
|--------|--------|---------|-------------|
| Production Data | Excel (.xlsx) | `s3://volve-landing/production/` | `bronze.raw_production` |
| WITSML XML | XML (11,664 files) | `s3://volve-landing/witsml/` | `bronze.witsml_*` |
| Well Logs | LAS (301 files) | `s3://volve-landing/well_logs/` | `bronze.raw_well_logs` |

---

## Key Business Rules

```python
# Derived columns (Silver layer)
water_cut = BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100  # NULL if denom=0
gas_oil_ratio = BORE_GAS_VOL / BORE_OIL_VOL  # NULL if oil=0
well_id = REGEXP_EXTRACT(WELL_BORE_CODE, 'F-[0-9]+')

# Alert thresholds (Gold layer)
is_anomaly_pressure = pressure_delta_24h > 500        # psi
is_zero_prod_uptime = (BORE_OIL_VOL == 0) AND (ON_STREAM_HRS > 0)
is_water_cut_spike  = (water_cut > 80) AND (lag_water_cut < 60)
is_gor_anomaly      = gas_oil_ratio > (well_baseline_gor * 3)

# Valid ranges
pressure_valid  = 0 <= AVG_DOWNHOLE_PRESSURE <= 10000  # psi
oil_vol_valid   = BORE_OIL_VOL >= 0
null_value_las  = -999.25  # Replace with NULL during LAS parsing
```

---

## Airflow DAG — 10 Tasks

```
Task 1:  check_source_files
Task 2:  run_glue_bronze_production     (parallel with Task 3)
Task 3:  run_glue_bronze_witsml         (parallel with Task 2)
Task 4:  run_silver_production          (parallel with Task 5)
Task 5:  run_silver_witsml              (parallel with Task 4)
Task 6:  check_dq_silver                (GATE — blocks downstream if fail)
Task 7:  run_gold_production            (parallel with Task 8)
Task 8:  run_gold_features              (parallel with Task 7)
Task 9:  run_ml_scoring
Task 10: send_daily_report
```

---

## MLflow Models (3)

| Model | Algorithm | Target |
|-------|-----------|--------|
| volve_pressure_prediction | XGBoost Regressor | next_day_pressure |
| volve_drilling_efficiency | Random Forest Regressor | rop_efficiency_score |
| volve_anomaly_detection | Isolation Forest | is_anomaly |

---

## DQ Targets

| Suite | Table | Target Pass Rate |
|-------|-------|-----------------|
| bronze_production_suite | bronze.raw_production | > 95% |
| silver_production_suite | silver.cleaned_production | > 95% |
| silver_witsml_suite | silver.cleaned_trajectory | > 95% |
| gold_feature_suite | gold.ml_feature_store | > 95% |

---

## What NOT To Do

```
❌ Jangan commit .env file
❌ Jangan commit actual credentials
❌ Jangan run NiFi + Airflow serentak
❌ Jangan run Databricks cluster bila tak guna (buang credit)
❌ Jangan process full 11,664 XML files — sample sahaja
❌ Jangan skip DQ gate even if in a hurry
```

---

## How To Resume Session

```
1. Buka PROJECT_STATUS.md — tengok "Next Step Bila Sambung"
2. Check docker ps — services apa yang running
3. Check Databricks cluster status — start kalau perlu
4. Sambung dari next step dalam PROJECT_STATUS.md
```

---

*Last updated: 2026-05-05*
EOF

echo "    ✅ CLAUDE.md"

# ── PROJECT_STATUS.md ──────────────────────────────────────
cat > PROJECT_STATUS.md << 'EOF'
# PROJECT_STATUS.md — Project Status Tracker
## Volve Sensor & Production Analytics Pipeline

**Kemaskini:** 2026-05-05
**Phase Semasa:** Phase 0 — Documentation & Setup

---

## Phase Overview

| Phase | Nama | Status |
|-------|------|--------|
| Phase 0 | Documentation & Repository Setup | ✅ Done |
| Phase 1 | Infrastructure Setup (NiFi, Airflow, S3) | ⏳ Pending |
| Phase 2 | Ingestion Layer (NiFi + Groovy) | ⏳ Pending |
| Phase 3 | Bronze Layer (AWS Glue) | ⏳ Pending |
| Phase 4 | Silver Layer (Databricks) | ⏳ Pending |
| Phase 5 | Gold Layer + Feature Store (Databricks) | ⏳ Pending |
| Phase 6 | ML Models (MLflow) | ⏳ Pending |
| Phase 7 | Orchestration (Airflow DAG) | ⏳ Pending |
| Phase 8 | Data Quality (Great Expectations) | ⏳ Pending |
| Phase 9 | Serving Layer (Snowflake) | ⏳ Pending |
| Phase 10 | Testing + Documentation Finalisation | ⏳ Pending |

---

## Siap ✅

- [x] Schema exploration — semua 3 sources explored
- [x] All 10 documentation files generated
- [x] Folder structure scaffolded (setup.sh executed)
- [x] .gitignore created
- [x] .env.example created
- [x] .mcp.json template created

---

## Next Step Bila Sambung

### Step 1: Authenticate semua tools
```
Ikut: infrastructure/credentials/SETUP_GUIDE.txt
Order: AWS CLI → Databricks CLI → NiFi Docker → Snowflake
```

### Step 2: Run pre-flight checks
```bash
aws sts get-caller-identity
databricks clusters list
curl -k https://localhost:8443/nifi-api/system/about
```

### Step 3: Buka Claude Code dalam VSCode
```
Ctrl+Shift+P → "Claude: Open"
Then run Prompt 2 (setup) → Prompt 3 (build pipeline)
```

---

## Known Issues / Blockers

| Issue | Severity | Notes |
|-------|----------|-------|
| Codespaces idle timeout kills containers | MEDIUM | Run `docker ps` bila start session |
| Databricks auto-terminate 2hr | MEDIUM | Set 30 min auto-terminate |
| NiFi + Airflow tak boleh serentak | LOW | Sequential execution |

---

## Decisions Made

| Decision | Reasoning |
|----------|-----------|
| 3 wells sahaja (F-1, F-11, F-12) | Free tier constraint |
| Docker Airflow instead of MWAA | Cost — $50/bulan vs free |
| Sequential execution | 8GB RAM constraint |
| Sample WITSML (~500 files) | Full dataset will timeout |
| Databricks Silver/Gold | $400 trial + MLflow built-in |

---

## Cost Tracking

| Service | Budget | Used | Remaining |
|---------|--------|------|-----------|
| Databricks | $400 | $0 | $400 |
| AWS S3 + Glue | ~$15 est. | $0 | ~$15 |
| Snowflake | 30-day trial | 0 days | 30 days |

---

*Kemaskini setiap kali stop kerja*
EOF

echo "    ✅ PROJECT_STATUS.md"

# ── docs/BRD.md ────────────────────────────────────────────
cat > docs/BRD.md << 'EOF'
# BRD — Business Requirements Document
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

---

## 1. Business Problem Statement

No automated pipeline exists to transform raw sensor and drilling data into
actionable intelligence for operations and data science teams.

---

## 2. Stakeholders

| Stakeholder | Role | Keperluan Utama |
|-------------|------|-----------------|
| Operations Team | Primary Consumer | Real-time monitoring, anomaly alerts, daily report |
| Data Science Team | Secondary Consumer | Clean feature store, ML model inputs |
| Data Engineering | Builder & Owner | Pipeline reliability, DQ enforcement |
| Field Management | Executive Viewer | Daily summary, KPI trends |

---

## 3. Business Requirements

### Operations Team

| ID | Keperluan | Priority |
|----|-----------|----------|
| BR-01 | Detect sensor anomali dalam masa < 5 minit | CRITICAL |
| BR-02 | Daily production report siap sebelum 6 AM | HIGH |
| BR-03 | Alert bila pressure drop > 500 psi dari 24-hr rolling avg | CRITICAL |
| BR-04 | Alert bila zero production tapi ON_STREAM_HRS > 0 | CRITICAL |
| BR-05 | Alert bila sensor flatline 3 readings berturut-turut | HIGH |
| BR-06 | Alert bila water cut spike > 80% | HIGH |
| BR-07 | Alert bila GOR > 3x well baseline | HIGH |

### Data Science Team

| ID | Keperluan | Priority |
|----|-----------|----------|
| BR-09 | Clean feature store di Gold layer | HIGH |
| BR-10 | 3 MLflow models: pressure, drilling, anomaly | HIGH |
| BR-11 | Historical data untuk backtesting | MEDIUM |

---

## 4. KPI Utama

| KPI | Target |
|-----|--------|
| Pipeline reliability | > 99% daily runs |
| Anomaly detection latency | < 5 minit |
| Silver layer SLA | Ready sebelum 6 AM |
| Forecast accuracy | MAPE < 15% |
| DQ pass rate | > 95% per suite |

---

## 5. Alert Thresholds

| Alert | Condition | Severity | Channel |
|-------|-----------|----------|---------|
| Pressure drop | > 500 psi dari 24-hr rolling avg | HIGH | Slack + Email |
| Zero production | BORE_OIL_VOL=0 & ON_STREAM_HRS>0 | CRITICAL | PagerDuty |
| Sensor flatline | Nilai sama 3 readings | MEDIUM | Email |
| Water cut spike | water_cut > 80% | HIGH | Slack + Email |
| GOR anomaly | GOR > 3x well baseline | HIGH | Slack + Email |

---

## 6. Business Rules & Definitions

| Term | Definisi |
|------|----------|
| Water Cut | BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) × 100 |
| GOR | BORE_GAS_VOL / BORE_OIL_VOL — null jika oil=0 |
| Pressure Drop Alert | AVG_DOWNHOLE_PRESSURE turun > 500 psi dari 24h avg |
| Valid Pressure Range | 0 – 10,000 psi |
| Valid Oil Volume | >= 0 (negative = quarantine) |

---

## 7. Constraints

| Constraint | Detail |
|------------|--------|
| Budget | AWS free tier + Databricks $400 + Snowflake 30-day trial |
| Codespaces | 2 core, 8GB RAM, 32GB storage |
| Wells in scope | F-1, F-11, F-12 only |
| Dataset | Sample — not full 11,664 XML files |

---

*Document Owner: Data Engineering Team*
EOF

echo "    ✅ docs/BRD.md"

# ── docs/DRD.md ────────────────────────────────────────────
cat > docs/DRD.md << 'EOF'
# DRD — Data Requirements Document
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

---

## 1. Source Systems Summary

| Source | Format | Files | Volume | Frequency |
|--------|--------|-------|--------|-----------|
| Production Data | Excel (.xlsx) | 1 file, 2 sheets | 15,634 rows | Daily batch |
| WITSML Drilling | XML | 11,664 files (sample ~500) | ~50MB sample | Daily batch |
| Well Logs | LAS | 301 files (sample ~30) | ~20MB sample | On-demand |

**Wells in scope:** F-1, F-11, F-12
**Landing Zone:** AWS S3 `s3://volve-landing/`

---

## 2. Source 1 — Production Data (Excel)

**File:** `Volve production data.xlsx`
**Sheet:** Daily Production Data (15,634 rows)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| DATEPRD | DATE | NO | Partition key |
| WELL_BORE_CODE | STRING | NO | Primary identifier |
| ON_STREAM_HRS | INT | NO | Hours on production |
| AVG_DOWNHOLE_PRESSURE | FLOAT | YES | psi |
| AVG_WHP_P | FLOAT | NO | Wellhead pressure psi |
| BORE_OIL_VOL | INT | NO | Daily oil Sm3 |
| BORE_GAS_VOL | INT | NO | Daily gas Sm3 |
| BORE_WAT_VOL | INT | NO | Daily water Sm3 |
| BORE_WI_VOL | FLOAT | YES | Water injection — all null |
| FLOW_KIND | STRING | NO | production/injection/test |
| WELL_TYPE | STRING | NO | WI/P |

---

## 3. Source 2 — WITSML XML

**Universal tags (ALL files):** name, dTimCreation, dTimLastChange, priv_dTimReceived, sourceName

**Trajectory-specific tags:** md, tvd, incl, azi, dTimStn, dls, dispNs, dispEw

**NiFi Routing Logic:**

| Folder Type | S3 Destination |
|-------------|----------------|
| _wellInfo | s3://volve-landing/witsml/well_info/ |
| _wellboreInfo | s3://volve-landing/witsml/wellbore_info/ |
| trajectory | s3://volve-landing/witsml/trajectory/ |
| message | s3://volve-landing/witsml/messages/ |
| bhaRun | s3://volve-landing/witsml/bha/ |
| Others | s3://volve-landing/witsml/other/ |

> ⚠️ 72 tags appear in SOME files only — handle missing tags gracefully

---

## 4. Source 3 — Well Logs (LAS)

**NULL value indicator:** -999.25 — WAJIB replace dengan NULL

**Common curves:** DEPT (universal), RPM, SWOB, TFLO, SPPA, GR_CAL, ECD, ROP

---

## 5. SLA Summary

| Layer | SLA |
|-------|-----|
| S3 Landing | Files arrive by 1 AM |
| Bronze complete | By 4 AM |
| Silver complete | By 5:30 AM |
| Gold complete | By 6 AM |
| Anomaly detection | < 5 minit dari landing |

---

## 6. Data Retention

| Layer | Retention | Storage |
|-------|-----------|---------|
| Bronze (S3) | Forever | Delta Lake |
| Silver (Databricks) | 3 tahun | Delta Lake |
| Gold (Snowflake) | 5 tahun | Snowflake tables |

---

*Document Owner: Data Engineering Team*
EOF

echo "    ✅ docs/DRD.md"

# ── docs/ARCHITECTURE.md ───────────────────────────────────
cat > docs/ARCHITECTURE.md << 'EOF'
# ARCHITECTURE.md — Solution Architecture Document
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

---

## 1. Architecture Overview

```
SOURCE (Excel + WITSML XML + LAS)
        ↓
[Apache NiFi + Groovy] — Route by format
        ↓
[AWS S3] — Bronze landing zone
        ↓
[AWS Glue PySpark] — Bronze transform
        ↓
[Databricks] — Silver (clean) → Gold (features + KPIs)
        ↓                ↓
[Snowflake]          [MLflow — 3 models]
Reporting views
        ↓
[Airflow 10-task DAG] — Orchestrate all
[Great Expectations]  — DQ gates
```

---

## 2. Layer Responsibilities

| Layer | Tool | Responsibility |
|-------|------|----------------|
| Ingestion | NiFi + Groovy | Route files, validate, land to S3 |
| Bronze | S3 + Glue | Raw as-is + metadata tagging |
| Silver | Databricks | Clean, dedupe, validate, derived columns |
| Gold | Databricks | KPIs, feature store, anomaly flags |
| Serving | Snowflake | Reporting views, BI consumption |
| Orchestration | Airflow | DAG scheduling, alerts |
| DQ | Great Expectations | Validation gates between layers |
| ML | MLflow (in Databricks) | Experiment tracking, model versioning |

---

## 3. Tool Justification

**NiFi vs Lambda:** NiFi pilih sebab O&G industry standard, native WITSML support, Groovy scripting built-in.

**Delta Lake vs Parquet:** Delta Lake pilih — ACID transactions, time travel, schema evolution, Z-Ordering.

**Glue vs Databricks (Bronze):** Glue pilih sebab S3-native dan cost effective. Databricks untuk Silver/Gold yang lebih compute-heavy.

**Docker Airflow vs MWAA:** Docker pilih — free vs ~$50/bulan. DAG code identical — resume claim valid.

---

## 4. Infrastructure Specs

| Resource | Spec | Notes |
|----------|------|-------|
| Codespaces CPU | 2 cores | Sequential execution |
| Codespaces RAM | 8GB | NiFi: ~2.5GB, Airflow: ~1.5GB |
| Codespaces Storage | 32GB | ~5GB used |
| Databricks | $400 trial | Auto-terminate 30 min |
| AWS S3 + Glue | ~$15 est. | Run once for demo |
| Snowflake | 30-day trial | X-Small warehouse |

---

## 5. Execution Modes (RAM Management)

| Mode | Services | RAM Used |
|------|----------|----------|
| Ingestion | NiFi ON, Airflow OFF | ~4GB |
| Orchestration | Airflow ON, NiFi OFF | ~3.5GB |
| Transform | Both OFF, scripts only | ~2GB |

---

## 6. Architecture Decision Records

### ADR-001: Delta Lake sebagai table format
**Decision:** Delta Lake 2.4+ untuk semua layers.
**Why:** ACID, time travel, schema evolution, MERGE operations.

### ADR-002: Sequential execution dalam Codespaces
**Decision:** NiFi dan Airflow jangan run serentak.
**Why:** 8GB RAM tak cukup buffer kalau run parallel.

### ADR-003: Docker Airflow ganti MWAA
**Decision:** Apache Airflow dalam Docker.
**Why:** Free vs $50/bulan. Code identical dengan MWAA.

### ADR-004: Sample dataset (3 wells, ~500 XML)
**Decision:** Wells F-1, F-11, F-12 sahaja.
**Why:** Full 11,664 files akan timeout + buang Databricks credit.

---

## 7. Security

| Layer | Method |
|-------|--------|
| AWS | IAM roles + .env (gitignored) |
| Databricks | Personal Access Token dalam .env |
| Snowflake | Username + password dalam .env |
| NiFi | Local Docker auth |
| Airflow | Fernet key + admin user |

---

*Document Owner: Data Engineering Team*
EOF

echo "    ✅ docs/ARCHITECTURE.md"

# ── docs/PIPELINE_SPEC.md ──────────────────────────────────
cat > docs/PIPELINE_SPEC.md << 'EOF'
# PIPELINE_SPEC.md — Pipeline Specification
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

---

## 1. NiFi Ingestion — Groovy Router

```groovy
// Route WITSML XML files by folder type
def filePath = flowFile.getAttribute('absolute.path') ?: ''
def routeDestination = 'other'

if (filePath.contains('_wellInfo'))         routeDestination = 'well_info'
else if (filePath.contains('_wellboreInfo')) routeDestination = 'wellbore_info'
else if (filePath.contains('/trajectory/')) routeDestination = 'trajectory'
else if (filePath.contains('/message/'))    routeDestination = 'messages'
else if (filePath.contains('/bhaRun/'))     routeDestination = 'bha'
else if (filePath.contains('/mudLog/'))     routeDestination = 'mud_log'

flowFile = session.putAttribute(flowFile, 'witsml.type', routeDestination)
flowFile = session.putAttribute(flowFile, 'ingestion.timestamp',
    new Date().format("yyyy-MM-dd'T'HH:mm:ss'Z'"))
session.transfer(flowFile, REL_SUCCESS)
```

---

## 2. Bronze Layer — AWS Glue

### bronze_production_daily.py
- Read Excel (both sheets)
- Add: ingestion_ts, source_file, well_id
- Cast DATEPRD → DATE
- Write Delta — partition by bronze_year, well_id
- **No cleaning** — raw as-is

### bronze_drilling_witsml.py
- Read XML by type folder
- Flatten XML tags → tabular
- Handle missing tags → NULL
- Write Delta per type — partition by well_name

### bronze_wellogs_las.py
- Read LAS via lasio library
- Extract header + curves
- Replace -999.25 → NULL
- Write Delta — partition by well_name, log_type

---

## 3. Silver Layer — Databricks

### silver_clean_production.py

```
Step 1: DEDUPLICATE — latest ingestion_ts per (DATEPRD, WELL_BORE_CODE)
Step 2: FILTER — wells F-1, F-11, F-12 + FLOW_KIND='production'
Step 3: TYPE CAST — DATEPRD→DATE, volumes→FLOAT
Step 4: NULL HANDLING
    WELL_BORE_CODE NULL → REJECT (quarantine)
    BORE_OIL_VOL NULL   → KEEP, flag is_oil_null=True
Step 5: DERIVED COLUMNS
    water_cut = BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100
    gas_oil_ratio = BORE_GAS_VOL / BORE_OIL_VOL
    well_id = REGEXP_EXTRACT(WELL_BORE_CODE, 'F-[0-9]+')
Step 6: WRITE — MERGE by (DATEPRD, WELL_BORE_CODE)
```

---

## 4. Gold Layer — Databricks

### gold_fact_production.py

| Column | Formula |
|--------|---------|
| pressure_delta_24h | pressure - LAG(pressure,1) OVER (PARTITION BY well_id ORDER BY date) |
| pressure_rolling_avg | AVG(pressure) OVER (7 PRECEDING) |
| is_anomaly_pressure | pressure_delta_24h > 500 |
| is_zero_prod_uptime | BORE_OIL_VOL=0 AND ON_STREAM_HRS>0 |
| is_water_cut_spike | water_cut>80 AND lag(water_cut)<60 |
| is_gor_anomaly | gas_oil_ratio > well_baseline_gor * 3 |

### gold_feature_store.py

**Model 1 — Pressure Prediction:**
Features: AVG_DOWNHOLE_PRESSURE lags, AVG_WHP_P, md, tvd, rolling avgs
Target: next_day_pressure

**Model 2 — Drilling Efficiency:**
Features: ROP, RPM, SWOB, SPPA, ECD, md (from LAS)
Target: rop_efficiency_score

**Model 3 — Production Anomaly:**
Features: ON_STREAM_HRS, volumes, rolling stats, water_cut, GOR, pressure_delta
Target: is_anomaly (binary)

---

## 5. MLflow Models

| Model | Algorithm | MLflow Experiment |
|-------|-----------|-------------------|
| Pressure Prediction | XGBoost Regressor | volve_pressure_prediction |
| Drilling Efficiency | Random Forest | volve_drilling_efficiency |
| Anomaly Detection | Isolation Forest | volve_anomaly_detection |

---

## 6. Airflow DAG — 10 Tasks

```
Task 1:  check_source_files
Task 2:  run_glue_bronze_production ─┐ parallel
Task 3:  run_glue_bronze_witsml     ─┘
Task 4:  run_silver_production      ─┐ parallel
Task 5:  run_silver_witsml          ─┘
Task 6:  check_dq_silver              ← DQ GATE
Task 7:  run_gold_production        ─┐ parallel
Task 8:  run_gold_features          ─┘
Task 9:  run_ml_scoring
Task 10: send_daily_report
```

Schedule: `0 2 * * *` | Retries: 3 | Retry delay: 5 min

---

## 7. Error Handling

| Scenario | Action |
|---------|--------|
| Source file missing | Skip, alert, pickup next run |
| XML parse error | Quarantine file, continue |
| NULL in critical field | Quarantine row, continue |
| DQ CRITICAL fail | Block Gold, alert immediately |
| Databricks timeout | Auto-restart, retry |

---

## 8. Partitioning Strategy

| Table | Partition | Z-Order |
|-------|-----------|---------|
| bronze.raw_production | bronze_year, well_id | DATEPRD |
| silver.cleaned_production | date_year, well_id | DATEPRD, WELL_BORE_CODE |
| gold.fact_daily_production | date_year, well_id | DATEPRD |
| gold.ml_feature_store | well_id | DATEPRD |

---

*Document Owner: Data Engineering Team*
EOF

echo "    ✅ docs/PIPELINE_SPEC.md"

# ── docs/DQD.md ────────────────────────────────────────────
cat > docs/DQD.md << 'EOF'
# DQD — Data Quality Document
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

---

## 1. DQ Dimensions

| Dimension | Check |
|-----------|-------|
| Completeness | WELL_BORE_CODE, DATEPRD NOT NULL |
| Accuracy | Pressure 0-10,000 psi, oil_vol >= 0 |
| Consistency | Bronze count ≈ Silver count (< 1% diff) |
| Uniqueness | No dupe per (DATEPRD, WELL_BORE_CODE) |
| Timeliness | Files in S3 by 1 AM |

---

## 2. Suite 1 — Bronze Production

**Suite:** `bronze_production_suite` | **Run:** Daily 3 AM

| Expectation | Column | Severity |
|-------------|--------|----------|
| not_be_null | WELL_BORE_CODE | CRITICAL |
| not_be_null | DATEPRD | CRITICAL |
| row_count 1-100,000 | — | CRITICAL |
| values_in_set | FLOW_KIND: [production,injection,test] | MEDIUM |

---

## 3. Suite 2 — Silver Production

**Suite:** `silver_production_suite` | **Run:** Daily 5:30 AM

| Expectation | Column | Config | Severity |
|-------------|--------|--------|----------|
| not_be_null | WELL_BORE_CODE | 100% | CRITICAL |
| not_be_null | DATEPRD | 100% | CRITICAL |
| be_between | AVG_DOWNHOLE_PRESSURE | 0-10,000, 99% | HIGH |
| be_between | BORE_OIL_VOL | min:0, 99% | HIGH |
| be_between | ON_STREAM_HRS | 0-24 | HIGH |
| be_unique | (DATEPRD, WELL_BORE_CODE) | — | HIGH |
| values_in_set | well_id | [F-1,F-11,F-12] | CRITICAL |

---

## 4. Suite 3 — Silver WITSML

**Suite:** `silver_witsml_suite` | **Run:** Daily 5:30 AM

| Expectation | Column | Severity |
|-------------|--------|----------|
| not_be_null | well_name | CRITICAL |
| be_between | md | 0-10,000 | HIGH |
| be_between | incl | 0-180 | HIGH |
| be_between | azi | 0-360 | MEDIUM |

---

## 5. Suite 4 — Gold Feature Store

**Suite:** `gold_feature_suite` | **Run:** Daily 6 AM

| Expectation | Column | Severity |
|-------------|--------|----------|
| not_be_null | well_id | CRITICAL |
| not_be_null | DATEPRD | CRITICAL |
| row_count >= 3 | — | CRITICAL |

---

## 6. Reconciliation Checks

| Check | Tolerance | Action |
|-------|-----------|--------|
| Bronze vs Silver count (production) | < 1% | Alert |
| Bronze vs Silver count (witsml) | < 5% | Alert if > 5% |
| Silver vs Gold (DATEPRD, well_id) | 0 missing | Block Snowflake |

---

## 7. Quarantine Table — silver.dq_quarantine

| Column | Type | Notes |
|--------|------|-------|
| quarantine_id | STRING | UUID |
| source_table | STRING | Origin |
| run_date | DATE | DQ run date |
| well_id | STRING | Affected well |
| row_data | STRING | JSON of row |
| failure_reason | STRING | Which expectation |
| severity | STRING | CRITICAL/HIGH/MEDIUM |
| resolved | BOOLEAN | Default False |

---

## 8. Action on Failure

| Severity | Action |
|----------|--------|
| CRITICAL | Block downstream + PagerDuty |
| HIGH | Quarantine bad rows + continue |
| MEDIUM | Flag rows (dq_flag=True) + continue |

---

## 9. Alert Thresholds

| Condition | Alert | Channel |
|-----------|-------|---------|
| Pass rate < 95% | WARNING | Slack |
| Pass rate < 90% | HIGH | Slack + Email |
| Any CRITICAL fail | CRITICAL | PagerDuty |
| Quarantine > 5% | HIGH | Slack + Email |

---

*Document Owner: Data Engineering Team*
EOF

echo "    ✅ docs/DQD.md"

# ── docs/OPS_RUNBOOK.md ────────────────────────────────────
cat > docs/OPS_RUNBOOK.md << 'EOF'
# OPS_RUNBOOK.md — Operations Runbook
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

---

## 1. Monitoring Endpoints

| Service | URL/Command |
|---------|-------------|
| Airflow UI | http://localhost:8080 |
| NiFi UI | https://localhost:8443/nifi |
| Databricks | https://community.cloud.databricks.com |
| DQ Results | SELECT * FROM silver.dq_results WHERE run_date = CURRENT_DATE |

---

## 2. Alert SLAs

| Severity | Channel | Response |
|----------|---------|----------|
| CRITICAL | PagerDuty | 15 minit |
| HIGH | Slack + Email | 1 jam |
| MEDIUM | Email | Hari bekerja |

---

## 3. Playbooks

### SCENARIO 1: Glue Job FAILED
```bash
# Check error
# AWS Console → Glue → Jobs → [job] → Runs → Error

# Fix: S3 file missing
aws s3 ls s3://volve-landing/production/

# Fix: Restart NiFi
docker restart nifi-container

# Rerun
airflow tasks clear volve_daily_pipeline -t run_glue_bronze_production --yes
```

### SCENARIO 2: Databricks Job FAILED
```bash
# Check Databricks UI → Jobs → Latest Run → Error

# Fix: Cluster terminated (most common)
databricks clusters start --cluster-id $DATABRICKS_CLUSTER_ID

# Fix: OOM
# Add in notebook: spark.conf.set("spark.sql.shuffle.partitions", "8")
```

### SCENARIO 3: DQ CRITICAL Fail
```sql
SELECT expectation_type, column_name, observed_value, rows_affected
FROM silver.dq_results
WHERE run_date = CURRENT_DATE AND severity = 'CRITICAL' AND success = FALSE;
```

### SCENARIO 4: NiFi Not Running
```bash
docker ps -a | grep nifi
docker start nifi-container
# Kalau container hilang:
docker run -d --name nifi-container -p 8443:8443 \
  -e SINGLE_USER_CREDENTIALS_USERNAME=admin \
  -e SINGLE_USER_CREDENTIALS_PASSWORD=adminpassword123 \
  apache/nifi:1.23.2
```

### SCENARIO 5: Airflow Not Running
```bash
docker-compose -f infrastructure/docker-compose.yml restart airflow-scheduler airflow-webserver
airflow dags trigger volve_daily_pipeline
```

---

## 4. Backfill Procedure

```bash
# Step 1: Clear Bronze partition
# In Databricks: spark.sql("DELETE FROM bronze.raw_production WHERE DATEPRD='2014-06-15'")

# Step 2: Trigger with date param
airflow dags trigger volve_daily_pipeline --conf '{"execution_date": "2014-06-15"}'

# Step 3: Verify
# Snowflake: SELECT * FROM silver.dq_results WHERE run_date = '2014-06-15'
```

---

## 5. Codespaces Session Checklist

### Start of Session
```bash
docker ps                         # Check running containers
export $(cat .env | xargs)        # Load env vars
databricks clusters list          # Check Databricks
```

### End of Session
```bash
docker stop $(docker ps -q)       # Stop all containers
# Stop Databricks cluster from UI (save credit)
# Update PROJECT_STATUS.md
```

---

## 6. Daily Ops Checklist

```
☐ Airflow: volve_daily_pipeline SUCCESS semalam?
☐ DQ: Pass rate > 95%?
☐ Quarantine: < 5% rows quarantined?
☐ Databricks cluster auto-terminated?
☐ Snowflake Gold data updated?
```

---

*Document Owner: Data Engineering Team*
EOF

echo "    ✅ docs/OPS_RUNBOOK.md"

# ── docs/MCP_SETUP.md ──────────────────────────────────────
cat > docs/MCP_SETUP.md << 'EOF'
# MCP_SETUP.md — MCP Installation & Configuration
## Volve Sensor & Production Analytics Pipeline

**Version:** 1.0 | **Last Updated:** 2026-05-05

> ⭐ Setup semua MCP SEBELUM bagi Claude Code start coding.
> Urutan: Install tools → Authenticate → Configure MCP → Test → Start Claude Code

---

## 1. MCPs Required

| MCP | Fungsi | Source |
|-----|--------|--------|
| AWS MCP | S3, Glue operations | github.com/awslabs/mcp |
| Databricks MCP | Clusters, notebooks, MLflow | Official CLI |
| NiFi MCP | NiFi flows, Groovy scripts | github.com/ms82119/NiFiMCP |

---

## 2. Prerequisites

```bash
# Verify semua tools ada
python3 --version     # >= 3.9
pip --version
docker --version
aws --version
databricks --version
node --version

# Install uv (required for AWS MCP)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv --version
```

---

## 3. AWS MCP Setup

```bash
# Test install
uvx awslabs.aws-documentation-mcp-server@latest --help
```

Add to `.mcp.json`:
```json
"aws-docs": {
  "command": "uvx",
  "args": ["awslabs.aws-documentation-mcp-server@latest"],
  "env": {"FASTMCP_LOG_LEVEL": "ERROR", "AWS_DOCUMENTATION_PARTITION": "aws"}
},
"aws-core": {
  "command": "uvx",
  "args": ["mcp-proxy-for-aws@latest", "https://aws-mcp.us-east-1.api.aws/mcp"]
}
```

---

## 4. Databricks MCP Setup

```bash
# Authenticate
databricks configure
# Host: https://community.cloud.databricks.com
# Token: [from Databricks UI → Settings → Developer → Access tokens]

# Verify
databricks clusters list
```

Add to `.mcp.json`:
```json
"databricks": {
  "command": "databricks",
  "args": ["mcp", "serve"],
  "env": {
    "DATABRICKS_HOST": "https://community.cloud.databricks.com",
    "DATABRICKS_TOKEN": "${DATABRICKS_TOKEN}"
  }
}
```

---

## 5. NiFi MCP Setup

```bash
# Step 1: Start NiFi Docker
docker run -d --name nifi-container \
  -p 8443:8443 \
  -e SINGLE_USER_CREDENTIALS_USERNAME=admin \
  -e SINGLE_USER_CREDENTIALS_PASSWORD=adminpassword123 \
  apache/nifi:1.23.2

# Wait ~3 minit for startup
docker logs nifi-container --tail 20

# Step 2: Clone and install NiFi MCP
cd /workspaces
git clone https://github.com/ms82119/NiFiMCP.git
cd NiFiMCP
python3 -m venv .venv
source .venv/bin/activate
pip install uv && uv sync
cp config.example.yaml config.yaml

# Step 3: Edit config.yaml
# nifi.url: "https://localhost:8443/nifi-api"
# nifi.verify_ssl: false
# llm.api_key: "$ANTHROPIC_API_KEY"

# Step 4: Start NiFi MCP server
uvicorn nifi_mcp_server.server:app --reload --port 8000 &

# Verify
curl http://localhost:8000/health
```

Add to `.mcp.json`:
```json
"nifi": {
  "command": "uvicorn",
  "args": ["nifi_mcp_server.server:app", "--port", "8000"],
  "cwd": "/workspaces/NiFiMCP",
  "env": {
    "NIFI_URL": "https://localhost:8443/nifi-api",
    "NIFI_USERNAME": "admin",
    "NIFI_PASSWORD": "adminpassword123"
  }
}
```

---

## 6. Pre-Flight Checklist

```bash
# Authentication
aws sts get-caller-identity                          # AWS ✅
databricks clusters list                             # Databricks ✅
curl -k https://localhost:8443/nifi-api/system/about # NiFi ✅
curl http://localhost:8000/health                    # NiFi MCP ✅

# S3 buckets
aws s3 ls | grep volve                               # Buckets exist ✅

# Claude Code
claude --version                                     # Installed ✅
# Open claude → "List my S3 buckets"                # AWS MCP works ✅
```

---

*Document Owner: Data Engineering Team*
EOF

echo "    ✅ docs/MCP_SETUP.md"

# ── infrastructure/credentials/SETUP_GUIDE.txt ────────────
cat > infrastructure/credentials/SETUP_GUIDE.txt << 'EOF'
=== SETUP GUIDE — AUTHENTICATE SEMUA TOOLS ===
=== Volve Sensor & Production Analytics Pipeline ===

URUTAN: AWS → Databricks → NiFi → Airflow → Snowflake → Claude Code

============================================================
STEP 1: AWS CLI
============================================================

$ aws configure
  AWS Access Key ID:     [your_access_key]
  AWS Secret Access Key: [your_secret_key]
  Default region:        ap-southeast-1
  Default output:        json

Verify:
  $ aws sts get-caller-identity

Create S3 buckets:
  $ aws s3 mb s3://volve-landing
  $ aws s3 mb s3://volve-bronze
  $ aws s3 mb s3://volve-silver

Upload dataset:
  $ aws s3 cp /path/to/volve/production/ s3://volve-landing/production/ --recursive
  $ aws s3 cp /path/to/volve/witsml/ s3://volve-landing/witsml/ --recursive

============================================================
STEP 2: DATABRICKS CLI
============================================================

Get token dari UI (BUKAN terminal):
  1. https://community.cloud.databricks.com
  2. Settings → Developer → Access tokens → Generate
  3. Description: volve-pipeline | Lifetime: 90 days
  4. COPY TOKEN — tak boleh tengok balik!
  5. Simpan dalam .env: DATABRICKS_TOKEN=dapi_xxx

Configure CLI:
  $ databricks configure
  Host:  https://community.cloud.databricks.com
  Token: [paste token]

Verify:
  $ databricks clusters list

Create cluster dari UI:
  Compute → Create compute
  Name: volve-pipeline-cluster
  Runtime: 14.3 LTS ML
  Auto terminate: 30 minutes ← WAJIB
  Copy cluster ID → simpan dalam .env: DATABRICKS_CLUSTER_ID=xxx

Setup AWS secrets dalam Databricks:
  $ databricks secrets create-scope --scope aws
  $ databricks secrets put --scope aws --key access-key \
      --string-value "$(aws configure get aws_access_key_id)"
  $ databricks secrets put --scope aws --key secret-key \
      --string-value "$(aws configure get aws_secret_access_key)"

============================================================
STEP 3: NIFI DOCKER
============================================================

⚠️ Jangan start Airflow dulu — RAM constraint!

Start NiFi:
  $ docker run -d \
      --name nifi-container \
      -p 8443:8443 \
      -e SINGLE_USER_CREDENTIALS_USERNAME=admin \
      -e SINGLE_USER_CREDENTIALS_PASSWORD=adminpassword123 \
      apache/nifi:1.23.2

Wait ~3 minit:
  $ docker logs nifi-container --tail 20

Access UI:
  Browser: https://localhost:8443/nifi
  Username: admin | Password: adminpassword123
  (Ignore SSL warning — click Advanced → Proceed)

Install NiFi MCP:
  $ cd /workspaces
  $ git clone https://github.com/ms82119/NiFiMCP.git
  $ cd NiFiMCP
  $ python3 -m venv .venv && source .venv/bin/activate
  $ pip install uv && uv sync
  $ cp config.example.yaml config.yaml
  Edit config.yaml — set nifi url, credentials, anthropic api_key

Start NiFi MCP:
  $ uvicorn nifi_mcp_server.server:app --reload --port 8000 &
  $ curl http://localhost:8000/health

============================================================
STEP 4: AIRFLOW DOCKER
============================================================

⚠️ Stop NiFi dulu: $ docker stop nifi-container

Generate Fernet key:
  $ python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  Simpan dalam .env: AIRFLOW_FERNET_KEY=[key]

Start Airflow:
  $ docker-compose -f infrastructure/docker-compose.yml up -d

Access UI:
  Browser: http://localhost:8080
  Username: airflow | Password: airflow

Add connections (Airflow UI → Admin → Connections):
  aws_default: Amazon Web Services + your keys
  databricks_default: Databricks + your token
  snowflake_default: Snowflake + your credentials

============================================================
STEP 5: SNOWFLAKE
============================================================

Create account: https://signup.snowflake.com (Trial, AWS, Singapore)

Setup (Snowflake worksheet):
  CREATE DATABASE VOLVE_DB;
  CREATE SCHEMA VOLVE_DB.BRONZE;
  CREATE SCHEMA VOLVE_DB.SILVER;
  CREATE SCHEMA VOLVE_DB.GOLD;
  CREATE WAREHOUSE COMPUTE_WH
    WAREHOUSE_SIZE='X-SMALL'
    AUTO_SUSPEND=60
    AUTO_RESUME=TRUE;

Simpan dalam .env:
  SNOWFLAKE_ACCOUNT=xxxx.ap-southeast-1
  SNOWFLAKE_USER=your_user
  SNOWFLAKE_PASSWORD=your_password

============================================================
STEP 6: CLAUDE CODE + MCP
============================================================

Load env vars:
  $ export $(cat .env | xargs)

Verify .mcp.json ada di root project

Start Claude Code:
  VSCode → Ctrl+Shift+P → Claude: Open
  ATAU terminal: $ claude

Test MCPs:
  "List my S3 buckets"           → AWS MCP works
  "List Databricks clusters"     → Databricks MCP works
  "Show NiFi flow status"        → NiFi MCP works

============================================================
PRE-FLIGHT CHECKLIST
============================================================

  $ aws sts get-caller-identity               ✅
  $ databricks clusters list                  ✅
  $ curl -k https://localhost:8443/nifi-api/system/about  ✅
  $ curl http://localhost:8000/health         ✅
  $ aws s3 ls | grep volve                    ✅
  $ cat .env | grep DATABRICKS_TOKEN          ✅
  $ cat .gitignore | grep ".env"              ✅

============================================================
TROUBLESHOOT
============================================================

  aws: command not found    → Install: curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip && unzip awscliv2.zip && sudo ./aws/install
  databricks: not found     → Install: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sudo sh
  NiFi 502 error            → Wait 3 more min, NiFi slow startup
  Databricks auth failed    → Token expired, re-run databricks configure
  NiFi + Airflow OOM        → Stop one before starting other

============================================================
Last updated: 2026-05-05
EOF

echo "    ✅ infrastructure/credentials/SETUP_GUIDE.txt"

# ────────────────────────────────────────────────────────────
# STEP 3: Create config files
# ────────────────────────────────────────────────────────────
echo ""
echo "[3/5] Creating config files..."

# ── .env.example ───────────────────────────────────────────
cat > .env.example << 'EOF'
# AWS
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=ap-southeast-1
AWS_S3_LANDING_BUCKET=volve-landing
AWS_S3_BRONZE_BUCKET=volve-bronze

# Databricks
DATABRICKS_HOST=https://community.cloud.databricks.com
DATABRICKS_TOKEN=dapi_your_token_here
DATABRICKS_CLUSTER_ID=your_cluster_id_here

# NiFi
NIFI_API_URL=https://localhost:8443/nifi-api
NIFI_USERNAME=admin
NIFI_PASSWORD=adminpassword123

# Snowflake
SNOWFLAKE_ACCOUNT=your_account_here
SNOWFLAKE_USER=your_user_here
SNOWFLAKE_PASSWORD=your_password_here
SNOWFLAKE_DATABASE=VOLVE_DB
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_SCHEMA=PUBLIC

# Anthropic (for NiFi MCP)
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Airflow
AIRFLOW_FERNET_KEY=your_fernet_key_here
AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
EOF

echo "    ✅ .env.example"

# ── .gitignore ─────────────────────────────────────────────
cat > .gitignore << 'EOF'
# Credentials — JANGAN COMMIT
.env
*.env
credentials/
**/*credentials*
*.key
*.pem

# Data files
*.parquet
*.csv
*.xlsx
*.las
*.xml
data/

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
env/
*.egg-info/
dist/
build/

# Databricks
.databricks/

# NiFi
NiFiMCP/config.yaml

# Logs
*.log
logs/
airflow/logs/

# Docker
docker-compose.override.yml

# IDE
.vscode/settings.json
.idea/

# OS
.DS_Store
Thumbs.db
EOF

echo "    ✅ .gitignore"

# ── .mcp.json ──────────────────────────────────────────────
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "aws-docs": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_DOCUMENTATION_PARTITION": "aws"
      }
    },
    "aws-core": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp"
      ]
    },
    "databricks": {
      "command": "databricks",
      "args": ["mcp", "serve"],
      "env": {
        "DATABRICKS_HOST": "https://community.cloud.databricks.com",
        "DATABRICKS_TOKEN": "${DATABRICKS_TOKEN}"
      }
    },
    "nifi": {
      "command": "uvicorn",
      "args": [
        "nifi_mcp_server.server:app",
        "--port", "8000"
      ],
      "cwd": "/workspaces/NiFiMCP",
      "env": {
        "NIFI_URL": "https://localhost:8443/nifi-api",
        "NIFI_USERNAME": "admin",
        "NIFI_PASSWORD": "adminpassword123"
      }
    }
  }
}
EOF

echo "    ✅ .mcp.json"

# ────────────────────────────────────────────────────────────
# STEP 4: Create placeholder HOW_IT_WORKS.txt per layer
# ────────────────────────────────────────────────────────────
echo ""
echo "[4/5] Creating HOW_IT_WORKS.txt placeholders..."

cat > ingestion/nifi/HOW_IT_WORKS.txt << 'EOF'
=== INGESTION LAYER — NiFi + Groovy ===

TUJUAN:
  Route 3 source formats (Excel, WITSML XML, LAS) ke S3 Bronze landing zone.

FILES:
  templates/volve_router.xml   - NiFi flow template (import ke NiFi UI)
  scripts/route_witsml.groovy  - Groovy script untuk route WITSML XML by folder type

FLOW ORDER:
  GetFile/ListS3 → RouteOnAttribute (by extension) → ExecuteGroovyScript → PutS3Object

CARA SETUP (BUKAN terminal — kena buat dari NiFi UI):
  Lihat: DASHBOARD_SETUP.txt

CARA TEST:
  Drop sample file ke watched folder, check S3 output:
  aws s3 ls s3://volve-landing/ --recursive
EOF

cat > ingestion/nifi/DASHBOARD_SETUP.txt << 'EOF'
=== NIFI DASHBOARD SETUP ===
=== Kena buat dari browser, BUKAN terminal ===

1. BUKA NIFI UI
   https://localhost:8443/nifi
   Username: admin | Password: adminpassword123

2. IMPORT FLOW TEMPLATE
   Upload → ingestion/nifi/templates/volve_router.xml
   Drag template ke canvas

3. CONFIGURE PROCESSOR SETTINGS
   GetFile → Input Directory: /data/volve-source
   PutS3Object → Bucket: volve-landing
   PutS3Object → Credentials: AWS credentials dari environment

4. START ALL PROCESSORS
   Right-click canvas → Start

5. MONITOR
   View → Summary → check processor status
   Green = running | Red = stopped | Yellow = warning
EOF

cat > bronze/glue_jobs/HOW_IT_WORKS.txt << 'EOF'
=== BRONZE LAYER — AWS Glue ===

TUJUAN:
  Ambil raw files dari S3 landing, tambah metadata, simpan sebagai Delta tables.
  NO cleaning at this layer — raw as-is.

FILES:
  bronze_production_daily.py  - Excel → Delta (partition: bronze_year, well_id)
  bronze_drilling_witsml.py   - WITSML XML → Delta (per folder type)
  bronze_wellogs_las.py       - LAS → Delta (partition: well_name, log_type)

METADATA ADDED (semua tables):
  ingestion_ts    TIMESTAMP  When file was processed
  source_file     STRING     Original filename
  source_system   STRING     production/witsml/well_logs
  well_id         STRING     F-1, F-11, F-12

CARA RUN:
  AWS Console → Glue → Jobs → [job_name] → Run
  ATAU via Airflow task run_glue_bronze_*

CARA DEBUG:
  AWS Console → Glue → Jobs → [job] → Runs → Logs
  Check CloudWatch logs kalau error
EOF

cat > silver/notebooks/HOW_IT_WORKS.txt << 'EOF'
=== SILVER LAYER — Databricks ===

TUJUAN:
  Clean, validate, deduplicate Bronze data. Add derived columns.
  Output: ready for Gold layer.

FILES:
  silver_clean_production.py  - Clean production Excel data
  silver_clean_witsml.py      - Clean WITSML XML data
  silver_clean_welllogs.py    - Clean LAS well log data
  silver_data_quality.py      - Run Great Expectations suites

CARA RUN MANUAL:
  python silver_clean_production.py --date 2013-01-15 --well F-1

CARA DEBUG:
  Check: airflow/logs/silver_clean_production/
  Check: SELECT * FROM silver.dq_quarantine WHERE run_date = CURRENT_DATE

LIHAT DATABRICKS_SETUP.txt untuk cara upload + run di Databricks UI
EOF

cat > silver/notebooks/DATABRICKS_SETUP.txt << 'EOF'
=== DATABRICKS SETUP — BUAT DI DASHBOARD ===

1. CREATE CLUSTER
   Compute → Create Compute
   Runtime: 14.3 LTS ML | Auto-terminate: 30 min

2. GENERATE TOKEN
   Settings → Developer → Access tokens → Generate
   Simpan: DATABRICKS_TOKEN=dapi_xxx

3. SETUP AWS SECRETS
   $ databricks secrets create-scope --scope aws
   $ databricks secrets put --scope aws --key access-key --string-value "$(aws configure get aws_access_key_id)"
   $ databricks secrets put --scope aws --key secret-key --string-value "$(aws configure get aws_secret_access_key)"

4. UPLOAD NOTEBOOK
   Workspace → Import → pilih .py file
   ATAU: databricks workspace import silver_clean_production.py /Shared/volve/silver/

5. RUN NOTEBOOK
   Attach ke cluster → Run All

TROUBLESHOOT:
  Cluster terminated → Restart dari Compute tab
  S3 access denied  → Check secrets scope
EOF

cat > gold/notebooks/HOW_IT_WORKS.txt << 'EOF'
=== GOLD LAYER — Databricks ===

TUJUAN:
  Aggregate Silver data. Calculate KPIs and anomaly flags.
  Build ML feature store.

FILES:
  gold_fact_production.py  - Daily production facts + anomaly flags
  gold_feature_store.py    - ML features untuk 3 models
  gold_aggregations.py     - Weekly + monthly aggregations
  gold_anomaly_batch.py    - Batch anomaly scoring

KEY BUSINESS RULES:
  water_cut = BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100
  gas_oil_ratio = BORE_GAS_VOL / BORE_OIL_VOL
  is_anomaly_pressure = pressure_delta_24h > 500
  is_zero_prod_uptime = (BORE_OIL_VOL=0 AND ON_STREAM_HRS>0)

OUTPUT TABLES:
  gold.fact_daily_production  - Main KPI table
  gold.ml_feature_store       - ML training features
  gold.agg_weekly_production  - Weekly rollups
  gold.agg_monthly_production - Monthly rollups
EOF

cat > gold/notebooks/DATABRICKS_SETUP.txt << 'EOF'
=== DATABRICKS SETUP — GOLD LAYER ===
Sama dengan silver/notebooks/DATABRICKS_SETUP.txt
Upload notebooks ke: /Shared/volve/gold/
EOF

cat > ml/training/HOW_IT_WORKS.txt << 'EOF'
=== ML LAYER — MLflow in Databricks ===

TUJUAN:
  Train 3 models menggunakan Gold feature store.
  Track experiments dengan MLflow.

FILES:
  train_pressure_prediction.py  - XGBoost: predict next_day_pressure
  train_drilling_efficiency.py  - Random Forest: predict ROP efficiency
  train_anomaly_detection.py    - Isolation Forest: detect anomalies

MLflow EXPERIMENTS:
  volve_pressure_prediction
  volve_drilling_efficiency
  volve_anomaly_detection

CARA VIEW RESULTS:
  Databricks UI → Machine Learning → Experiments

LIHAT MLFLOW_SETUP.txt untuk model registry dan stage transitions
EOF

cat > ml/training/MLFLOW_SETUP.txt << 'EOF'
=== MLFLOW SETUP — Databricks UI ===

1. VIEW EXPERIMENTS
   Databricks → Machine Learning → Experiments

2. REGISTER MODEL
   Experiment run → Register Model
   Name: volve_pressure_prediction (etc.)

3. STAGE TRANSITIONS
   Models → [model] → Version → Transition to Production

4. LOAD MODEL IN NOTEBOOK
   import mlflow
   model = mlflow.sklearn.load_model("models:/volve_pressure_prediction/Production")
EOF

cat > data_quality/HOW_IT_WORKS.txt << 'EOF'
=== DATA QUALITY — Great Expectations ===

TUJUAN:
  Validate data antara layers.
  Block downstream kalau CRITICAL expectation fail.

SUITES (4):
  bronze_production_suite    - Bronze layer validation
  silver_production_suite    - Silver production validation (DQ GATE)
  silver_witsml_suite        - Silver WITSML validation
  gold_feature_suite         - Gold feature store validation

CARA RUN:
  great_expectations suite list
  great_expectations checkpoint run volve_silver_checkpoint

RESULTS:
  HTML docs: data_quality/great_expectations/uncommitted/data_docs/
  DB table:  silver.dq_results
  Quarantine: silver.dq_quarantine
EOF

cat > airflow/dags/HOW_IT_WORKS.txt << 'EOF'
=== AIRFLOW ORCHESTRATION ===

TUJUAN:
  Orchestrate seluruh pipeline dalam 10-task DAG.

DAGs:
  volve_daily_pipeline.py    - Main pipeline DAG
  volve_streaming_monitor.py - Anomaly monitoring DAG

SCHEDULE: 0 2 * * * (2 AM daily)

10-TASK ORDER:
  1. check_source_files
  2. run_glue_bronze_production  (parallel with 3)
  3. run_glue_bronze_witsml      (parallel with 2)
  4. run_silver_production       (parallel with 5)
  5. run_silver_witsml           (parallel with 4)
  6. check_dq_silver             ← DQ GATE
  7. run_gold_production         (parallel with 8)
  8. run_gold_features           (parallel with 7)
  9. run_ml_scoring
  10. send_daily_report

CARA TRIGGER MANUAL:
  Airflow UI → DAG → Trigger ▶
  ATAU: airflow dags trigger volve_daily_pipeline
EOF

cat > airflow/MWAA_SETUP.txt << 'EOF'
=== AIRFLOW SETUP — Docker (portfolio) ===

NOTE: Guna Docker Airflow untuk portfolio demo.
      Code adalah identical dengan AWS MWAA.

START AIRFLOW:
  ⚠️ Stop NiFi dulu: docker stop nifi-container

  $ docker-compose -f infrastructure/docker-compose.yml up -d

ACCESS UI:
  http://localhost:8080
  Username: airflow | Password: airflow

STOP AIRFLOW:
  $ docker-compose -f infrastructure/docker-compose.yml down

UNTUK AWS MWAA (production reference):
  AWS Console → MWAA → Create environment
  Upload DAG files ke S3 → MWAA auto-syncs
  Same DAG code works without modification
EOF

cat > tests/HOW_IT_WORKS.txt << 'EOF'
=== TESTS ===

unit/        - Unit tests per function/script
integration/ - End-to-end pipeline tests

RUN TESTS:
  pytest tests/unit/ -v
  pytest tests/integration/ -v

COVERAGE:
  pytest --cov=. tests/
EOF

echo "    ✅ All HOW_IT_WORKS.txt created"

# ────────────────────────────────────────────────────────────
# STEP 5: Git init
# ────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Initialising git repository..."

git init
git add .
git commit -m "feat: initial project scaffold with full documentation"

echo "    ✅ Git repository initialised"

# ────────────────────────────────────────────────────────────
# DONE
# ────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " ✅ Setup complete!"
echo "============================================================"
echo ""
echo " Files created:"
echo "   CLAUDE.md"
echo "   PROJECT_STATUS.md"
echo "   .env.example"
echo "   .gitignore"
echo "   .mcp.json"
echo "   docs/ (7 documents)"
echo "   infrastructure/credentials/SETUP_GUIDE.txt"
echo "   All layer folders with HOW_IT_WORKS.txt"
echo ""
echo " Next steps:"
echo "   1. cp .env.example .env"
echo "   2. Fill in .env with your actual credentials"
echo "   3. Follow infrastructure/credentials/SETUP_GUIDE.txt"
echo "   4. Open Claude Code: Ctrl+Shift+P → Claude: Open"
echo "   5. Run Prompt 2 (setup) then Prompt 3 (build pipeline)"
echo ""
echo " Prompts ada dalam: docs/MCP_SETUP.md"
echo "============================================================"

