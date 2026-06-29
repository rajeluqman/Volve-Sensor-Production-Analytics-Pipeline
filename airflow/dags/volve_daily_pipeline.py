"""
Volve Daily Pipeline DAG
10-task orchestration for the Volve Sensor & Production Analytics Pipeline.
Schedule : 0 2 * * * (2 AM daily)

Dependency chain:
  t1 → [t2, t3] → [t4, t5] → t6 → [t7, t8] → t9 → t10

Architecture note: pipeline runs scripts locally (Codespaces) which connect to
Databricks SQL Warehouse (claudecatalog). No AWS Glue — all transforms via Databricks SQL.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from operators.databricks_sql_operator import (
    DatabricksSQLQueryOperator,
    DatabricksSQLScriptOperator,
)

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(
    os.environ.get("VOLVE_PROJECT_ROOT", Path(__file__).parent.parent.parent)
)


def _notify_slack_failure(context: dict) -> None:
    """Slack alerting backfill (this repo had none — `01_OPUS_DECISIONS.md` flagged Volve as a
    Slack-backfill repo like olist, ported from CIL's `_notify_slack_failure` pattern in
    `dags/creative_intel_pipeline.py`). Graceful no-op if SLACK_WEBHOOK_URL is unset — alerting
    being unconfigured must never raise a second failure on top of the real one."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        log.warning("SLACK_WEBHOOK_URL not set — skipping Slack alert (credentials not filled in yet)")
        return

    ti = context["task_instance"]
    text = (
        f":red_circle: *Volve pipeline task failed*\n"
        f"*DAG:* `{ti.dag_id}`  *Task:* `{ti.task_id}`\n"
        f"*Run:* `{context.get('run_id', '?')}`\n"
        f"<{ti.log_url}|View logs>"
    )
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info("Slack alert sent (status %s)", resp.status)
    except Exception as e:  # noqa: BLE001 — alerting must never raise into the task's own failure handling
        log.warning("Slack alert failed to send: %s", e)


DEFAULT_ARGS = {
    "owner":            "volve-pipeline",
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
    "email_on_failure": False,
    "on_failure_callback": _notify_slack_failure,
    "email_on_retry":   False,
}

# --- SQL: Task 1 — verify source volume and catalog schemas exist ---
SOURCE_CHECK_SQL = [
    "CREATE SCHEMA IF NOT EXISTS claudecatalog.bronze",
    "CREATE SCHEMA IF NOT EXISTS claudecatalog.silver",
    "CREATE SCHEMA IF NOT EXISTS claudecatalog.gold",
    # Verify source volume is reachable
    """
    SELECT COUNT(*) AS file_count
    FROM read_files(
        '/Volumes/equinor_asa_volve_data_village/public/volve/Production_data/',
        format => 'binaryFile'
    )
    """,
]

# --- SQL: Task 6 — DQ gate checks against silver tables ---
# Each SELECT returns (check_name STRING, passed BOOLEAN).
DQ_CHECKS_SQL = """
SELECT check_name, passed FROM (
    SELECT 'silver_prod_row_count'    AS check_name,
           COUNT(*) > 100             AS passed
    FROM   claudecatalog.silver.cleaned_production

    UNION ALL

    SELECT 'silver_prod_dateprd_null' AS check_name,
           (SUM(CASE WHEN DATEPRD IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) < 5
                                      AS passed
    FROM   claudecatalog.silver.cleaned_production

    UNION ALL

    SELECT 'silver_prod_well_null'    AS check_name,
           (SUM(CASE WHEN well_id IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) < 5
                                      AS passed
    FROM   claudecatalog.silver.cleaned_production

    UNION ALL

    SELECT 'silver_prod_water_cut_range' AS check_name,
           (SUM(CASE WHEN water_cut_pct < 0 OR water_cut_pct > 100 THEN 1 ELSE 0 END)
            * 100.0 / NULLIF(COUNT(*), 0)) < 10
                                      AS passed
    FROM   claudecatalog.silver.cleaned_production

    UNION ALL

    SELECT 'silver_traj_row_count'    AS check_name,
           COUNT(*) > 0               AS passed
    FROM   claudecatalog.silver.cleaned_trajectory
)
"""


def _send_daily_report(**context):
    """Query Gold tables and print a summary report. Never raises — report is informational."""
    import os

    from databricks import sql as dbsql
    from dotenv import load_dotenv

    load_dotenv()
    host      = os.environ["DATABRICKS_HOST"].replace("https://", "")
    http_path = os.environ["DATABRICKS_HTTP_PATH"]
    token     = os.environ["DATABRICKS_TOKEN"]

    production_sql = """
    SELECT
        well_id,
        MAX(DATEPRD)                                                         AS last_date,
        ROUND(SUM(BORE_OIL_VOL), 0)                                          AS total_oil_sm3,
        ROUND(SUM(BORE_GAS_VOL) / 1e6, 3)                                   AS total_gas_msm3,
        ROUND(AVG(water_cut_7d_avg), 2)                                      AS avg_water_cut_7d,
        SUM(CASE WHEN is_anomaly_pressure = true THEN 1 ELSE 0 END)          AS pressure_anomalies
    FROM claudecatalog.gold.production_daily
    WHERE DATEPRD >= DATE_SUB(CURRENT_DATE(), 7)
    GROUP BY well_id
    ORDER BY well_id
    """

    anomaly_sql = """
    SELECT COALESCE(COUNT(*), 0) AS total_anomalies
    FROM claudecatalog.gold.ml_predictions
    WHERE pred_is_anomaly = 1
      AND DATEPRD >= DATE_SUB(CURRENT_DATE(), 1)
    """

    run_date = context.get("ds", str(datetime.utcnow().date()))
    print("\n" + "=" * 62)
    print(f"  VOLVE DAILY REPORT — {run_date}")
    print("=" * 62)

    try:
        with dbsql.connect(
            server_hostname=host, http_path=http_path, access_token=token
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(production_sql)
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]

            print("\n  Production Summary (last 7 days):")
            header = f"  {'Well':<8} {'Last Date':<12} {'Oil (sm³)':<12} {'Gas (Msm³)':<12} {'WaterCut%':<11} {'Alerts'}"
            print(header)
            print("  " + "-" * 62)
            for row in rows:
                r = dict(zip(cols, row))
                print(
                    f"  {str(r['well_id']):<8} "
                    f"{str(r['last_date']):<12} "
                    f"{str(r['total_oil_sm3']):<12} "
                    f"{str(r['total_gas_msm3']):<12} "
                    f"{str(r['avg_water_cut_7d']):<11} "
                    f"{r['pressure_anomalies']}"
                )

            with conn.cursor() as cur:
                cur.execute(anomaly_sql)
                anomaly_count = cur.fetchone()[0]

            print(f"\n  ML Anomalies (last 24h) : {anomaly_count}")

    except Exception as e:
        print(f"\n  [WARN] Report query failed: {e}")

    print("=" * 62 + "\n")


with DAG(
    dag_id="volve_daily_pipeline",
    description="Volve Sensor & Production Analytics — 10-task daily pipeline",
    schedule="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["volve", "oil-gas", "databricks"],
    max_active_runs=1,
) as dag:

    # Task 1 — verify source volume and schemas
    t1_check_source = DatabricksSQLQueryOperator(
        task_id="check_source_files",
        sql=SOURCE_CHECK_SQL,
    )

    # Tasks 2 & 3 — Bronze (parallel)
    t2_bronze_prod = DatabricksSQLScriptOperator(
        task_id="run_glue_bronze_production",
        script_path=str(PROJECT_ROOT / "bronze" / "bronze_production.py"),
    )

    t3_bronze_witsml = DatabricksSQLScriptOperator(
        task_id="run_glue_bronze_witsml",
        script_path=str(PROJECT_ROOT / "bronze" / "bronze_witsml.py"),
    )

    # Tasks 4 & 5 — Silver (parallel)
    t4_silver_prod = DatabricksSQLScriptOperator(
        task_id="run_silver_production",
        script_path=str(PROJECT_ROOT / "silver" / "silver_production.py"),
    )

    t5_silver_witsml = DatabricksSQLScriptOperator(
        task_id="run_silver_witsml",
        script_path=str(PROJECT_ROOT / "silver" / "silver_trajectory.py"),
    )

    # Task 6 — DQ gate (blocks downstream on failure)
    t6_dq_gate = DatabricksSQLQueryOperator(
        task_id="check_dq_silver",
        sql=DQ_CHECKS_SQL,
        validation_mode=True,
    )

    # Tasks 7 & 8 — Gold (parallel)
    t7_gold_prod = DatabricksSQLScriptOperator(
        task_id="run_gold_production",
        script_path=str(PROJECT_ROOT / "gold" / "gold_production_daily.py"),
    )

    t8_gold_features = DatabricksSQLScriptOperator(
        task_id="run_gold_features",
        script_path=str(PROJECT_ROOT / "gold" / "gold_ml_features.py"),
    )

    # Task 9 — ML batch scoring (scores last 30 days from feature store)
    t9_ml_scoring = DatabricksSQLScriptOperator(
        task_id="run_ml_scoring",
        script_path=str(PROJECT_ROOT / "ml" / "score_models.py"),
        script_args=["--days", "30"],
    )

    # Task 10 — Daily summary report
    t10_report = PythonOperator(
        task_id="send_daily_report",
        python_callable=_send_daily_report,
    )

    # Dependency chain
    # list >> list is not supported in Airflow 2.x — fan-out each upstream manually
    t1_check_source >> [t2_bronze_prod, t3_bronze_witsml]
    t2_bronze_prod >> [t4_silver_prod, t5_silver_witsml]
    t3_bronze_witsml >> [t4_silver_prod, t5_silver_witsml]
    [t4_silver_prod, t5_silver_witsml] >> t6_dq_gate
    t6_dq_gate >> [t7_gold_prod, t8_gold_features]
    [t7_gold_prod, t8_gold_features] >> t9_ml_scoring
    t9_ml_scoring >> t10_report
