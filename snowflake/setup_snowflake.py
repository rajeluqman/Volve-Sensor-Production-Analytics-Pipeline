"""
Phase 8 — Snowflake Serving Layer
setup_snowflake.py: Create database, schema, warehouse, and staging tables.
Run once before load_snowflake.py.
"""

import os
import sys
import logging
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── DDL ──────────────────────────────────────────────────────────────────────

DDL_SETUP = """
CREATE DATABASE IF NOT EXISTS VOLVE_DB;
CREATE SCHEMA IF NOT EXISTS VOLVE_DB.SERVING;
"""

DDL_PRODUCTION_DAILY = """
CREATE TABLE IF NOT EXISTS VOLVE_DB.SERVING.production_daily (
    well_id                  VARCHAR(20),
    DATEPRD                  DATE,
    date_year                INT,
    WELL_BORE_CODE           VARCHAR(50),
    BORE_OIL_VOL             FLOAT,
    BORE_GAS_VOL             FLOAT,
    BORE_WAT_VOL             FLOAT,
    ON_STREAM_HRS            FLOAT,
    AVG_DOWNHOLE_PRESSURE    FLOAT,
    water_cut_pct            FLOAT,
    gas_oil_ratio            FLOAT,
    pressure_delta_24h       FLOAT,
    is_anomaly_pressure      BOOLEAN,
    is_zero_prod_uptime      BOOLEAN,
    is_water_cut_spike       BOOLEAN,
    is_gor_anomaly           BOOLEAN,
    oil_vol_7d_avg           FLOAT,
    oil_vol_30d_avg          FLOAT,
    gas_vol_7d_avg           FLOAT,
    gas_vol_30d_avg          FLOAT,
    water_cut_7d_avg         FLOAT,
    water_cut_30d_avg        FLOAT,
    pressure_7d_avg          FLOAT,
    pressure_30d_avg         FLOAT,
    cum_oil_vol_monthly      FLOAT,
    cum_gas_vol_monthly      FLOAT,
    loaded_at                TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
"""

DDL_ML_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS VOLVE_DB.SERVING.ml_predictions (
    well_id                  VARCHAR(20),
    DATEPRD                  DATE,
    predicted_pressure       FLOAT,
    rop_efficiency_score     FLOAT,
    anomaly_score            FLOAT,
    is_predicted_anomaly     BOOLEAN,
    prediction_date          TIMESTAMP_NTZ,
    loaded_at                TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
"""

# ── Snowflake connection ──────────────────────────────────────────────────────

def get_conn():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    )


def run_statement(cur, sql: str, label: str):
    sql = sql.strip()
    if not sql:
        return
    cur.execute(sql)
    log.info("OK  %s", label)


def setup():
    log.info("Connecting to Snowflake …")
    conn = get_conn()
    cur = conn.cursor()

    try:
        for stmt in DDL_SETUP.strip().split(";"):
            run_statement(cur, stmt, stmt.strip()[:60])

        cur.execute("USE DATABASE VOLVE_DB")
        cur.execute("USE SCHEMA SERVING")

        run_statement(cur, DDL_PRODUCTION_DAILY, "CREATE TABLE production_daily")
        run_statement(cur, DDL_ML_PREDICTIONS,   "CREATE TABLE ml_predictions")

        log.info("Snowflake setup complete — VOLVE_DB.SERVING ready")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    try:
        setup()
    except Exception as exc:
        log.error("Setup failed: %s", exc)
        sys.exit(1)
