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
