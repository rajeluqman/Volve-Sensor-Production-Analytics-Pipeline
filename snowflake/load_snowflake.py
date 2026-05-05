"""
Phase 8 — Snowflake Serving Layer
load_snowflake.py: ETL from Databricks Gold tables → Snowflake SERVING.
Run after setup_snowflake.py has created the target tables.
"""

import os
import sys
import logging
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from databricks import sql as dbsql
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── Databricks ────────────────────────────────────────────────────────────────

def _databricks_conn():
    return dbsql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"].replace("https://", ""),
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def fetch_databricks(query: str) -> pd.DataFrame:
    conn = _databricks_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            arrow_table = cur.fetchall_arrow()
            return arrow_table.to_pandas()
    finally:
        conn.close()


# ── Snowflake ─────────────────────────────────────────────────────────────────

def _snowflake_conn():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database="VOLVE_DB",
        schema="SERVING",
    )


def _truncate_and_load(sf_conn, df: pd.DataFrame, table: str, label: str):
    # Snowflake unquoted identifiers are uppercase; match DataFrame columns
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]

    cur = sf_conn.cursor()
    cur.execute(f"TRUNCATE TABLE VOLVE_DB.SERVING.{table}")
    cur.close()

    success, nchunks, nrows, _ = write_pandas(
        sf_conn, df, table.upper(), quote_identifiers=False
    )
    log.info("  %-28s  %d rows  (%d chunks)  success=%s", label, nrows, nchunks, success)


# ── Queries ───────────────────────────────────────────────────────────────────

QUERY_PRODUCTION = """
SELECT
    well_id,
    DATEPRD,
    date_year,
    WELL_BORE_CODE,
    BORE_OIL_VOL,
    BORE_GAS_VOL,
    BORE_WAT_VOL,
    ON_STREAM_HRS,
    AVG_DOWNHOLE_PRESSURE,
    water_cut_pct,
    gas_oil_ratio,
    pressure_delta_24h,
    is_anomaly_pressure,
    is_zero_prod_uptime,
    is_water_cut_spike,
    is_gor_anomaly,
    oil_vol_7d_avg,
    oil_vol_30d_avg,
    gas_vol_7d_avg,
    gas_vol_30d_avg,
    water_cut_7d_avg,
    water_cut_30d_avg,
    pressure_7d_avg,
    pressure_30d_avg,
    cum_oil_vol_monthly,
    cum_gas_vol_monthly
FROM claudecatalog.gold.production_daily
ORDER BY well_id, DATEPRD
"""

QUERY_ML = """
SELECT
    well_id,
    DATEPRD,
    predicted_pressure,
    rop_efficiency_score,
    anomaly_score,
    is_predicted_anomaly,
    prediction_date
FROM claudecatalog.gold.ml_predictions
ORDER BY well_id, DATEPRD
"""


# ── Load functions ────────────────────────────────────────────────────────────

def load_production_daily(sf_conn):
    log.info("Fetching production_daily from Databricks …")
    df = fetch_databricks(QUERY_PRODUCTION)
    log.info("  Fetched %d rows from claudecatalog.gold.production_daily", len(df))
    _truncate_and_load(sf_conn, df, "production_daily", "SERVING.production_daily")


def load_ml_predictions(sf_conn):
    log.info("Fetching ml_predictions from Databricks …")
    try:
        df = fetch_databricks(QUERY_ML)
        log.info("  Fetched %d rows from claudecatalog.gold.ml_predictions", len(df))
        _truncate_and_load(sf_conn, df, "ml_predictions", "SERVING.ml_predictions")
    except Exception as exc:
        # ml_predictions created by Airflow Task 9 — may not exist yet
        log.warning("  ml_predictions not available (Airflow Task 9 not run yet): %s", exc)


def load():
    log.info("=== Phase 8 — Load: Databricks Gold → Snowflake ===")
    sf_conn = _snowflake_conn()
    try:
        load_production_daily(sf_conn)
        load_ml_predictions(sf_conn)
        log.info("Load complete.")
    finally:
        sf_conn.close()


if __name__ == "__main__":
    try:
        load()
    except Exception as exc:
        log.error("Load failed: %s", exc)
        sys.exit(1)
