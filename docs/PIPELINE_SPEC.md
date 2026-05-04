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
