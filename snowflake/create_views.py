"""
Phase 8 — Snowflake Serving Layer
create_views.py: Create 5 BI reporting views in VOLVE_DB.SERVING.
Run after load_snowflake.py has populated the staging tables.
"""

import os
import sys
import logging
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── View DDL ──────────────────────────────────────────────────────────────────

VIEWS = {
    "vw_daily_production_kpis": """
        CREATE OR REPLACE VIEW VOLVE_DB.SERVING.vw_daily_production_kpis AS
        SELECT
            well_id,
            DATEPRD,
            date_year,
            BORE_OIL_VOL,
            BORE_GAS_VOL,
            BORE_WAT_VOL,
            ON_STREAM_HRS,
            AVG_DOWNHOLE_PRESSURE,
            water_cut_pct,
            gas_oil_ratio,
            pressure_delta_24h,
            oil_vol_7d_avg,
            oil_vol_30d_avg,
            gas_vol_7d_avg,
            gas_vol_30d_avg,
            water_cut_7d_avg,
            water_cut_30d_avg,
            pressure_7d_avg,
            pressure_30d_avg,
            cum_oil_vol_monthly,
            cum_gas_vol_monthly,
            is_anomaly_pressure,
            is_zero_prod_uptime,
            is_water_cut_spike,
            is_gor_anomaly
        FROM VOLVE_DB.SERVING.production_daily
        ORDER BY well_id, DATEPRD
    """,

    "vw_anomaly_alerts": """
        CREATE OR REPLACE VIEW VOLVE_DB.SERVING.vw_anomaly_alerts AS
        SELECT
            well_id,
            DATEPRD,
            AVG_DOWNHOLE_PRESSURE,
            pressure_delta_24h,
            water_cut_pct,
            gas_oil_ratio,
            is_anomaly_pressure,
            is_zero_prod_uptime,
            is_water_cut_spike,
            is_gor_anomaly,
            (CASE WHEN is_anomaly_pressure  THEN 1 ELSE 0 END +
             CASE WHEN is_zero_prod_uptime  THEN 1 ELSE 0 END +
             CASE WHEN is_water_cut_spike   THEN 1 ELSE 0 END +
             CASE WHEN is_gor_anomaly       THEN 1 ELSE 0 END) AS anomaly_count,
            CASE
                WHEN is_anomaly_pressure AND is_water_cut_spike THEN 'CRITICAL'
                WHEN is_anomaly_pressure OR is_water_cut_spike OR is_gor_anomaly THEN 'HIGH'
                WHEN is_zero_prod_uptime THEN 'MEDIUM'
                ELSE 'LOW'
            END AS alert_severity
        FROM VOLVE_DB.SERVING.production_daily
        WHERE is_anomaly_pressure
           OR is_zero_prod_uptime
           OR is_water_cut_spike
           OR is_gor_anomaly
        ORDER BY DATEPRD DESC, alert_severity
    """,

    "vw_production_trends": """
        CREATE OR REPLACE VIEW VOLVE_DB.SERVING.vw_production_trends AS
        SELECT
            well_id,
            DATE_TRUNC('month', DATEPRD)    AS production_month,
            date_year,
            COUNT(*)                        AS production_days,
            SUM(BORE_OIL_VOL)               AS total_oil_vol,
            SUM(BORE_GAS_VOL)               AS total_gas_vol,
            SUM(BORE_WAT_VOL)               AS total_wat_vol,
            SUM(ON_STREAM_HRS)              AS total_on_stream_hrs,
            AVG(water_cut_pct)              AS avg_water_cut_pct,
            AVG(gas_oil_ratio)              AS avg_gor,
            AVG(AVG_DOWNHOLE_PRESSURE)      AS avg_pressure,
            MAX(cum_oil_vol_monthly)        AS cum_oil_vol_monthly,
            MAX(cum_gas_vol_monthly)        AS cum_gas_vol_monthly,
            SUM(CASE WHEN is_anomaly_pressure THEN 1 ELSE 0 END) AS anomaly_days
        FROM VOLVE_DB.SERVING.production_daily
        GROUP BY well_id, DATE_TRUNC('month', DATEPRD), date_year
        ORDER BY well_id, production_month
    """,

    "vw_ml_predictions": """
        CREATE OR REPLACE VIEW VOLVE_DB.SERVING.vw_ml_predictions AS
        SELECT
            p.well_id,
            p.DATEPRD,
            p.AVG_DOWNHOLE_PRESSURE                             AS actual_pressure,
            m.predicted_pressure,
            ABS(p.AVG_DOWNHOLE_PRESSURE - m.predicted_pressure) AS pressure_abs_error,
            m.rop_efficiency_score,
            m.anomaly_score,
            m.is_predicted_anomaly,
            p.is_anomaly_pressure                               AS actual_anomaly,
            CASE
                WHEN m.is_predicted_anomaly AND p.is_anomaly_pressure THEN 'TRUE_POS'
                WHEN m.is_predicted_anomaly AND NOT p.is_anomaly_pressure THEN 'FALSE_POS'
                WHEN NOT m.is_predicted_anomaly AND p.is_anomaly_pressure THEN 'FALSE_NEG'
                ELSE 'TRUE_NEG'
            END                                                 AS prediction_result,
            m.prediction_date
        FROM VOLVE_DB.SERVING.production_daily p
        LEFT JOIN VOLVE_DB.SERVING.ml_predictions m
            ON p.well_id = m.well_id AND p.DATEPRD = m.DATEPRD
        ORDER BY p.well_id, p.DATEPRD
    """,

    "vw_well_comparison": """
        CREATE OR REPLACE VIEW VOLVE_DB.SERVING.vw_well_comparison AS
        SELECT
            well_id,
            date_year,
            COUNT(*)                                                    AS active_days,
            SUM(BORE_OIL_VOL)                                           AS total_oil_vol,
            SUM(BORE_GAS_VOL)                                           AS total_gas_vol,
            SUM(BORE_WAT_VOL)                                           AS total_wat_vol,
            SUM(ON_STREAM_HRS)                                          AS total_on_stream_hrs,
            AVG(water_cut_pct)                                          AS avg_water_cut_pct,
            AVG(gas_oil_ratio)                                          AS avg_gor,
            AVG(AVG_DOWNHOLE_PRESSURE)                                  AS avg_pressure,
            AVG(oil_vol_30d_avg)                                        AS avg_30d_oil_vol,
            AVG(pressure_30d_avg)                                       AS avg_30d_pressure,
            SUM(CASE WHEN is_anomaly_pressure  THEN 1 ELSE 0 END)       AS anomaly_pressure_days,
            SUM(CASE WHEN is_water_cut_spike   THEN 1 ELSE 0 END)       AS water_cut_spike_days,
            SUM(CASE WHEN is_gor_anomaly       THEN 1 ELSE 0 END)       AS gor_anomaly_days,
            SUM(CASE WHEN is_zero_prod_uptime  THEN 1 ELSE 0 END)       AS zero_prod_uptime_days,
            ROUND(
                SUM(CASE WHEN is_anomaly_pressure THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                2
            )                                                           AS anomaly_pct
        FROM VOLVE_DB.SERVING.production_daily
        GROUP BY well_id, date_year
        ORDER BY well_id, date_year
    """,
}


# ── Main ──────────────────────────────────────────────────────────────────────

def get_conn():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database="VOLVE_DB",
        schema="SERVING",
    )


def create_views():
    log.info("=== Phase 8 — Create BI Views in VOLVE_DB.SERVING ===")
    conn = get_conn()
    cur = conn.cursor()
    try:
        for view_name, ddl in VIEWS.items():
            cur.execute(ddl.strip())
            log.info("  OK  %s", view_name)
        log.info("All 5 views created.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    try:
        create_views()
    except Exception as exc:
        log.error("View creation failed: %s", exc)
        sys.exit(1)
