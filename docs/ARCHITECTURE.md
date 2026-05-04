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
