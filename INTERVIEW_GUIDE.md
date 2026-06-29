# INTERVIEW_GUIDE.md — Volve Sensor & Production Analytics Pipeline

> Co-owned by @business-analyst (evidence content) and @documentation-sherpa (structure). Every
> resume bullet must trace to `file:line` evidence or be flagged unsupported — never softened
> by omission, never fabricated by invention.

## Resume Claim ↔ Repo Evidence

| Resume claim | Evidence | Verdict |
|---|---|---|
| "Databricks Lakehouse, Bronze→Silver→Gold via SQL Warehouse" | `bronze/bronze_production.py`, `silver/silver_production.py`, `gold/gold_production_daily.py` — all use `databricks-sql-connector` + `read_files()`/SQL DDL, no PySpark cluster | ✅ Supported |
| "3 MLflow models: pressure, drilling efficiency, anomaly detection" | `ml/train_pressure_prediction.py` (XGBoost), `ml/train_drilling_efficiency.py` (Random Forest), `ml/train_anomaly_detection.py` (Isolation Forest) | ✅ Supported |
| "10-task Airflow DAG with DQ gate" | `airflow/dags/volve_daily_pipeline.py` — 10 tasks (`t1`...`t10`), `check_dq_silver` blocks Gold tasks on failure | ✅ Supported |
| "Snowflake BI serving layer, 5 views" | `snowflake/create_views.py` — `vw_daily_production_kpis`, `vw_anomaly_alerts`, `vw_production_trends`, `vw_ml_predictions`, `vw_well_comparison` | ✅ Supported |
| **"84 tests, 0 failures"** | `find tests -type f` → 1 file, `tests/HOW_IT_WORKS.txt` (a stub, not a test). Zero `.py` test files exist anywhere in the repo. | ❌ **Unsupported.** Recommend removing this claim until @senior-data-engineer builds real tests (deferred per `CLAUDE.md`/`PROJECT_STATUS.md`), or softening to "test suite planned, not yet implemented." |
| **"Data Quality enforced via Great Expectations, Phase 7 Done"** (README, pre-correction) | `data_quality/` contains only `HOW_IT_WORKS.txt`. No GE suite files exist. The real DQ gate is 5 inline SQL checks in `airflow/dags/volve_daily_pipeline.py`'s `DQ_CHECKS_SQL`. | ❌ **Unsupported as originally worded** — README corrected this retrofit to describe the real inline-SQL gate; recommend resume wording say "inline SQL data-quality gate in the Airflow DAG" not "Great Expectations". |
| "NiFi-based ingestion routing" (if ever claimed) | `ingestion/nifi/` is a `HOW_IT_WORKS.txt`-only stub, references a `route_witsml.groovy` that was never built. ADR-001 explicitly states NiFi was replaced by direct Databricks Volume access. | ❌ **Unsupported** — do not claim NiFi was used in this pipeline. |
| "AWS Glue ingestion" (if ever claimed) | `bronze/glue_jobs/` is a `HOW_IT_WORKS.txt`-only stub, references scripts (`bronze_production_daily.py`, etc.) that were never built. Real ingestion is `bronze/bronze_production.py`/`bronze_witsml.py` via Databricks SQL Warehouse. | ❌ **Unsupported** |
| "3 wells from the Volve open dataset (F-1, F-11, F-12)" | `silver/silver_production.py` `well_id IN ('F-1', 'F-11', 'F-12')`, `docs/ADR/ADR-005-three-well-scope.md` | ✅ Supported |
| "Slack alerting on pipeline failure" | Backfilled this retrofit — `airflow/dags/volve_daily_pipeline.py` `_notify_slack_failure`, `on_failure_callback`. Was NOT present before 2026-06-29. | ✅ Supported as of this retrofit — note the date if asked "when did you add this" |

## Honest framing for the interview
This repo is a strong demonstration of a real Databricks-native lakehouse pipeline with working
ML and BI serving. The honest gap to be ready to discuss: the documentation set (BRD/DRD/DQD/
PIPELINE_SPEC) lagged behind a real architecture pivot (NiFi+Glue → direct Databricks Volume
access, ADR-001) and was never updated — a realistic, common failure mode worth naming
proactively rather than getting caught flat if an interviewer reads the stale docs first. The
test suite and GE-suite gaps are real and should be framed as a known next step, not glossed
over.
