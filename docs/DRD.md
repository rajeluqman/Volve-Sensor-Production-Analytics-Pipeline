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
