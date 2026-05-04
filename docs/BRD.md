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
