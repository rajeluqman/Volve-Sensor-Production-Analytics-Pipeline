#!/usr/bin/env python3
"""
Gold Layer — ML Feature Store
Sources : claudecatalog.silver.cleaned_production
          claudecatalog.silver.cleaned_trajectory
Target  : claudecatalog.gold.ml_feature_store (Delta, partitioned by date_year + well_id)

Feature groups:
  - Raw production metrics (passthrough from silver)
  - Temporal features         : day_of_week, month_num
  - Lag features              : pressure_lag1/2/3/7, water_cut_lag1, gor_lag1
  - Rolling means 7-day       : pressure, oil_vol, water_cut, gor
  - Rolling means 30-day      : pressure, oil_vol, water_cut, gor
  - Volatility (std 7-day)    : pressure_7d_std, oil_vol_7d_std
  - Cumulative production     : cum_oil_vol, cum_gas_vol (well lifetime)
  - Well characteristics      : total_md_m, max_tvd_m, avg_incl_deg, avg_dls (from trajectory)

Target variables (one table serves all 3 MLflow models):
  - next_day_pressure    → volve_pressure_prediction    (XGBoost Regressor)
  - rop_efficiency_score → volve_drilling_efficiency    (Random Forest Regressor)
  - is_anomaly           → volve_anomaly_detection      (Isolation Forest)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from databricks import sql

load_dotenv(Path(__file__).parent.parent / ".env")

HOST      = os.environ["DATABRICKS_HOST"].replace("https://", "")
HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
TOKEN     = os.environ["DATABRICKS_TOKEN"]

PROD_TABLE = "claudecatalog.silver.cleaned_production"
TRAJ_TABLE = "claudecatalog.silver.cleaned_trajectory"
TARGET_TABLE = "claudecatalog.gold.ml_feature_store"

SQL_CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS claudecatalog.gold"
SQL_DROP_TABLE    = f"DROP TABLE IF EXISTS {TARGET_TABLE}"

# rop_efficiency_score: proxy for well production efficiency.
#   = (BORE_OIL_VOL / ON_STREAM_HRS) / (total_md_m / 1000)
#   Units: Sm3/hr per km of wellbore depth — normalises shallow vs deep wells.
#   NULL when ON_STREAM_HRS = 0 or trajectory data missing.
#
# is_anomaly: composite of all three CLAUDE.md anomaly rules (OR logic).
#   Used as binary target for Isolation Forest training.
#
# baseline_gor: full-well-history average — stable denominator.
# WINDOW w: unbounded lag/lead window, reused for all lag/lead functions.
SQL_CREATE_TABLE = f"""
CREATE TABLE {TARGET_TABLE}
USING DELTA
COMMENT 'Gold ML feature store. One row per (DATEPRD, well_id). Contains lag/rolling features and three model target variables: next_day_pressure, rop_efficiency_score, is_anomaly.'
PARTITIONED BY (date_year, well_id)
AS
WITH traj_stats AS (
  SELECT
    well_id,
    MAX(md_m)                                                      AS total_md_m,
    MAX(tvd_m)                                                     AS max_tvd_m,
    AVG(CASE WHEN is_md_valid AND is_incl_valid THEN incl_deg END) AS avg_incl_deg,
    AVG(CASE WHEN dls_deg_per_30m IS NOT NULL
             THEN dls_deg_per_30m END)                             AS avg_dls,
    COUNT(*)                                                       AS n_survey_stations
  FROM {TRAJ_TABLE}
  WHERE is_md_valid
  GROUP BY well_id
),
prod_windowed AS (
  SELECT
    DATEPRD,
    well_id,
    date_year,
    BORE_OIL_VOL,
    BORE_GAS_VOL,
    BORE_WAT_VOL,
    ON_STREAM_HRS,
    AVG_DOWNHOLE_PRESSURE,
    AVG_DOWNHOLE_TEMPERATURE,
    AVG_WHP_P,
    AVG_ANNULUS_PRESS,
    water_cut_pct,
    gas_oil_ratio,
    is_zero_prod_uptime,

    -- Temporal features
    DAYOFWEEK(DATEPRD)              AS day_of_week,
    MONTH(DATEPRD)                  AS month_num,

    -- Lag features (for sequence modelling and delta computation)
    LAG(AVG_DOWNHOLE_PRESSURE, 1) OVER w AS pressure_lag1,
    LAG(AVG_DOWNHOLE_PRESSURE, 2) OVER w AS pressure_lag2,
    LAG(AVG_DOWNHOLE_PRESSURE, 3) OVER w AS pressure_lag3,
    LAG(AVG_DOWNHOLE_PRESSURE, 7) OVER w AS pressure_lag7,
    LAG(water_cut_pct,          1) OVER w AS water_cut_lag1,
    LAG(gas_oil_ratio,          1) OVER w AS gor_lag1,

    -- Rolling means (7-day)
    AVG(AVG_DOWNHOLE_PRESSURE)  OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS pressure_7d_avg,
    AVG(BORE_OIL_VOL)           OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS oil_vol_7d_avg,
    AVG(water_cut_pct)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS water_cut_7d_avg,
    AVG(gas_oil_ratio)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS gor_7d_avg,

    -- Rolling means (30-day)
    AVG(AVG_DOWNHOLE_PRESSURE)  OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS pressure_30d_avg,
    AVG(BORE_OIL_VOL)           OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS oil_vol_30d_avg,
    AVG(water_cut_pct)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS water_cut_30d_avg,
    AVG(gas_oil_ratio)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS gor_30d_avg,

    -- Volatility (7-day std dev)
    STDDEV(AVG_DOWNHOLE_PRESSURE) OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS pressure_7d_std,
    STDDEV(BORE_OIL_VOL)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS oil_vol_7d_std,

    -- Cumulative production (well lifetime, resets only at partition boundary)
    SUM(BORE_OIL_VOL) OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_oil_vol,
    SUM(BORE_GAS_VOL) OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_gas_vol,

    -- Baseline GOR for is_gor_anomaly (stable well-level mean)
    AVG(gas_oil_ratio) OVER (PARTITION BY well_id) AS baseline_gor,

    -- Target 1: next-day pressure for regression model
    LEAD(AVG_DOWNHOLE_PRESSURE, 1) OVER w AS next_day_pressure

  FROM {PROD_TABLE}
  WINDOW w AS (PARTITION BY well_id ORDER BY DATEPRD)
)
SELECT
  p.DATEPRD,
  p.well_id,
  p.date_year,

  -- Raw production metrics
  p.BORE_OIL_VOL,
  p.BORE_GAS_VOL,
  p.BORE_WAT_VOL,
  p.ON_STREAM_HRS,
  p.AVG_DOWNHOLE_PRESSURE,
  p.AVG_DOWNHOLE_TEMPERATURE,
  p.AVG_WHP_P,
  p.AVG_ANNULUS_PRESS,
  p.water_cut_pct,
  p.gas_oil_ratio,
  p.is_zero_prod_uptime,

  -- Temporal features
  p.day_of_week,
  p.month_num,

  -- Lag features
  p.pressure_lag1,
  p.pressure_lag2,
  p.pressure_lag3,
  p.pressure_lag7,
  p.water_cut_lag1,
  p.gor_lag1,

  -- Rolling averages (7-day)
  p.pressure_7d_avg,
  p.oil_vol_7d_avg,
  p.water_cut_7d_avg,
  p.gor_7d_avg,

  -- Rolling averages (30-day)
  p.pressure_30d_avg,
  p.oil_vol_30d_avg,
  p.water_cut_30d_avg,
  p.gor_30d_avg,

  -- Volatility features
  p.pressure_7d_std,
  p.oil_vol_7d_std,

  -- Cumulative production
  p.cum_oil_vol,
  p.cum_gas_vol,

  -- Pressure delta (derived anomaly feature)
  CASE
    WHEN p.AVG_DOWNHOLE_PRESSURE IS NOT NULL AND p.pressure_lag1 IS NOT NULL
    THEN ABS(p.AVG_DOWNHOLE_PRESSURE - p.pressure_lag1)
    ELSE NULL
  END AS pressure_delta_24h,

  -- Well trajectory characteristics (static per well, joined from silver)
  t.total_md_m,
  t.max_tvd_m,
  t.avg_incl_deg,
  t.avg_dls,
  t.n_survey_stations,

  -- === TARGET VARIABLES ===

  -- Target 1: volve_pressure_prediction (XGBoost Regressor)
  p.next_day_pressure,

  -- Target 2: volve_drilling_efficiency (Random Forest Regressor)
  -- Proxy: oil production per uptime-hour per km of wellbore depth
  CASE
    WHEN p.ON_STREAM_HRS > 0
     AND t.total_md_m IS NOT NULL
     AND t.total_md_m > 0
    THEN (p.BORE_OIL_VOL / p.ON_STREAM_HRS) / (t.total_md_m / 1000.0)
    ELSE NULL
  END AS rop_efficiency_score,

  -- Target 3: volve_anomaly_detection (Isolation Forest)
  -- OR of all three CLAUDE.md anomaly rules
  CASE
    WHEN (
      p.AVG_DOWNHOLE_PRESSURE IS NOT NULL AND p.pressure_lag1 IS NOT NULL
      AND ABS(p.AVG_DOWNHOLE_PRESSURE - p.pressure_lag1) > 500
    )
    OR (
      p.water_cut_pct IS NOT NULL AND p.water_cut_lag1 IS NOT NULL
      AND p.water_cut_pct > 80 AND p.water_cut_lag1 < 60
    )
    OR (
      p.gas_oil_ratio IS NOT NULL AND p.baseline_gor IS NOT NULL
      AND p.baseline_gor > 0
      AND p.gas_oil_ratio > p.baseline_gor * 3
    )
    THEN TRUE ELSE FALSE
  END AS is_anomaly,

  current_timestamp() AS processed_ts

FROM prod_windowed p
LEFT JOIN traj_stats t ON p.well_id = t.well_id
"""

SQL_ROW_COUNT = f"SELECT COUNT(*) FROM {TARGET_TABLE}"

SQL_TARGET_COVERAGE = f"""
  SELECT
    well_id,
    COUNT(*)                                                         AS total_rows,
    SUM(CASE WHEN next_day_pressure    IS NOT NULL THEN 1 ELSE 0 END) AS has_pressure_target,
    SUM(CASE WHEN rop_efficiency_score IS NOT NULL THEN 1 ELSE 0 END) AS has_rop_target,
    SUM(CASE WHEN is_anomaly                       THEN 1 ELSE 0 END) AS anomaly_count,
    SUM(CASE WHEN total_md_m           IS NOT NULL THEN 1 ELSE 0 END) AS has_trajectory,
    ROUND(AVG(pressure_7d_avg), 1)                                   AS avg_pressure_7d,
    ROUND(AVG(water_cut_7d_avg), 2)                                  AS avg_water_cut_7d
  FROM {TARGET_TABLE}
  GROUP BY well_id
  ORDER BY well_id
"""

SQL_FEATURE_NULLS = f"""
  SELECT
    SUM(CASE WHEN pressure_lag1       IS NULL THEN 1 ELSE 0 END) AS null_pressure_lag1,
    SUM(CASE WHEN pressure_7d_avg     IS NULL THEN 1 ELSE 0 END) AS null_pressure_7d,
    SUM(CASE WHEN oil_vol_7d_avg      IS NULL THEN 1 ELSE 0 END) AS null_oil_7d,
    SUM(CASE WHEN total_md_m          IS NULL THEN 1 ELSE 0 END) AS null_total_md,
    SUM(CASE WHEN next_day_pressure   IS NULL THEN 1 ELSE 0 END) AS null_pressure_target,
    SUM(CASE WHEN rop_efficiency_score IS NULL THEN 1 ELSE 0 END) AS null_rop_target
  FROM {TARGET_TABLE}
"""


def run():
    print(f"\n{'='*60}")
    print("Gold Layer — ML Feature Store")
    print(f"{'='*60}")
    print(f"Sources : {PROD_TABLE}")
    print(f"          {TRAJ_TABLE}")
    print(f"Target  : {TARGET_TABLE}\n")

    with sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    ) as conn:
        with conn.cursor() as cur:

            print("[1/6] Creating schema claudecatalog.gold (if not exists)...")
            cur.execute(SQL_CREATE_SCHEMA)
            print("      OK")

            print(f"[2/6] Dropping existing table {TARGET_TABLE}...")
            cur.execute(SQL_DROP_TABLE)
            print("      OK")

            print(f"[3/6] Creating {TARGET_TABLE}...")
            print("      (CTAS with joins + window functions — may take ~2 min)")
            cur.execute(SQL_CREATE_TABLE)
            print("      OK")

            print("[4/6] Verifying row count...")
            cur.execute(SQL_ROW_COUNT)
            total = cur.fetchone()[0]
            print(f"      Total rows : {total:,}")

            print("[5/6] Target variable coverage by well...")
            cur.execute(SQL_TARGET_COVERAGE)
            rows = cur.fetchall()
            print(f"\n{'Well':<8} {'Rows':>6}  {'PressTarget':>12}  {'ROPTarget':>10}  {'Anomalies':>10}  {'HasTraj':>8}  {'P7d':>8}  {'WC7d':>7}")
            print("-" * 80)
            for row in rows:
                well, total_r, pt, rt, ac, ht, p7d, wc7d = row
                p7d_s  = f"{p7d:.1f}"  if p7d  is not None else "N/A"
                wc7d_s = f"{wc7d:.2f}" if wc7d is not None else "N/A"
                print(f"{str(well):<8} {int(total_r):>6}  {int(pt):>12}  {int(rt):>10}  {int(ac):>10}  {int(ht):>8}  {p7d_s:>8}  {wc7d_s:>7}")

            print("\n[6/6] Feature NULL check...")
            cur.execute(SQL_FEATURE_NULLS)
            nr = cur.fetchone()
            null_p_lag, null_p7d, null_oil7d, null_md, null_pt, null_rt = nr
            print(f"      null pressure_lag1     : {null_p_lag}")
            print(f"      null pressure_7d_avg   : {null_p7d}")
            print(f"      null oil_vol_7d_avg    : {null_oil7d}")
            print(f"      null total_md_m        : {null_md}  (expected — trajectory coverage)")
            print(f"      null next_day_pressure : {null_pt}  (last row per well has no LEAD)")
            print(f"      null rop_efficiency    : {null_rt}")

    print(f"\nDone. {TARGET_TABLE} is ready.\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
