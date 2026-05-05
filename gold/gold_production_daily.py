#!/usr/bin/env python3
"""
Gold Layer — Production Daily KPIs
Source : claudecatalog.silver.cleaned_production
Target : claudecatalog.gold.production_daily (Delta, partitioned by date_year + well_id)

Adds on top of Silver:
  - pressure_delta_24h  : ABS(today - yesterday pressure)
  - Anomaly flags       : is_anomaly_pressure, is_water_cut_spike, is_gor_anomaly
  - Rolling averages    : 7-day and 30-day for oil/gas/water/pressure/water_cut
  - Monthly cumulative  : cum_oil_vol_monthly, cum_gas_vol_monthly
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

SOURCE_TABLE = "claudecatalog.silver.cleaned_production"
TARGET_TABLE = "claudecatalog.gold.production_daily"

SQL_CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS claudecatalog.gold"
SQL_DROP_TABLE    = f"DROP TABLE IF EXISTS {TARGET_TABLE}"

# baseline_gor: full-well-history average — stable denominator for is_gor_anomaly.
# is_anomaly_pressure: |delta| > 500 psi per CLAUDE.md business rules.
# is_water_cut_spike : today > 80% AND yesterday < 60% (step-change detection).
# is_gor_anomaly     : today > 3x well baseline GOR.
# Monthly cumulative windows restart at the 1st of each calendar month.
SQL_CREATE_TABLE = f"""
CREATE TABLE {TARGET_TABLE}
USING DELTA
COMMENT 'Gold: daily production KPIs per well with rolling averages, pressure deltas, and anomaly flags. One row per (DATEPRD, well_id).'
PARTITIONED BY (date_year, well_id)
AS
WITH base AS (
  SELECT
    DATEPRD,
    well_id,
    WELL_BORE_CODE,
    date_year,
    BORE_OIL_VOL,
    BORE_GAS_VOL,
    BORE_WAT_VOL,
    BORE_WI_VOL,
    ON_STREAM_HRS,
    AVG_DOWNHOLE_PRESSURE,
    AVG_DOWNHOLE_TEMPERATURE,
    AVG_ANNULUS_PRESS,
    AVG_WHP_P,
    AVG_WHT_P,
    water_cut_pct,
    gas_oil_ratio,
    is_zero_prod_uptime,
    is_pressure_valid
  FROM {SOURCE_TABLE}
),
enriched AS (
  SELECT
    *,

    -- Prior-day values for delta and spike detection
    LAG(AVG_DOWNHOLE_PRESSURE, 1) OVER (PARTITION BY well_id ORDER BY DATEPRD) AS prev_pressure,
    LAG(water_cut_pct,          1) OVER (PARTITION BY well_id ORDER BY DATEPRD) AS prev_water_cut_pct,

    -- Well-level baseline GOR (full history average, used as anomaly denominator)
    AVG(gas_oil_ratio) OVER (PARTITION BY well_id)                              AS baseline_gor,

    -- 7-day rolling averages
    AVG(BORE_OIL_VOL)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS oil_vol_7d_avg,
    AVG(BORE_GAS_VOL)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS gas_vol_7d_avg,
    AVG(BORE_WAT_VOL)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS wat_vol_7d_avg,
    AVG(AVG_DOWNHOLE_PRESSURE) OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS pressure_7d_avg,
    AVG(water_cut_pct)         OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS water_cut_7d_avg,

    -- 30-day rolling averages
    AVG(BORE_OIL_VOL)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS oil_vol_30d_avg,
    AVG(BORE_GAS_VOL)          OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS gas_vol_30d_avg,
    AVG(AVG_DOWNHOLE_PRESSURE) OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS pressure_30d_avg,
    AVG(water_cut_pct)         OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS water_cut_30d_avg,

    -- Monthly cumulative volumes (resets each calendar month)
    SUM(BORE_OIL_VOL) OVER (
      PARTITION BY well_id, date_year, MONTH(DATEPRD)
      ORDER BY DATEPRD
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cum_oil_vol_monthly,
    SUM(BORE_GAS_VOL) OVER (
      PARTITION BY well_id, date_year, MONTH(DATEPRD)
      ORDER BY DATEPRD
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cum_gas_vol_monthly

  FROM base
)
SELECT
  DATEPRD,
  well_id,
  WELL_BORE_CODE,
  date_year,

  -- Raw volumes and operational metrics
  BORE_OIL_VOL,
  BORE_GAS_VOL,
  BORE_WAT_VOL,
  BORE_WI_VOL,
  ON_STREAM_HRS,
  AVG_DOWNHOLE_PRESSURE,
  AVG_DOWNHOLE_TEMPERATURE,
  AVG_ANNULUS_PRESS,
  AVG_WHP_P,
  AVG_WHT_P,

  -- Silver KPIs passthrough
  water_cut_pct,
  gas_oil_ratio,
  is_zero_prod_uptime,
  is_pressure_valid,

  -- Gold: 24-hour pressure change
  CASE
    WHEN AVG_DOWNHOLE_PRESSURE IS NOT NULL AND prev_pressure IS NOT NULL
    THEN ABS(AVG_DOWNHOLE_PRESSURE - prev_pressure)
    ELSE NULL
  END AS pressure_delta_24h,

  -- Gold: 7-day rolling averages
  oil_vol_7d_avg,
  gas_vol_7d_avg,
  wat_vol_7d_avg,
  pressure_7d_avg,
  water_cut_7d_avg,

  -- Gold: 30-day rolling averages
  oil_vol_30d_avg,
  gas_vol_30d_avg,
  pressure_30d_avg,
  water_cut_30d_avg,

  -- Gold: monthly cumulative volumes
  cum_oil_vol_monthly,
  cum_gas_vol_monthly,

  -- Gold: anomaly flags (per CLAUDE.md business rules)
  CASE
    WHEN AVG_DOWNHOLE_PRESSURE IS NOT NULL AND prev_pressure IS NOT NULL
     AND ABS(AVG_DOWNHOLE_PRESSURE - prev_pressure) > 500
    THEN TRUE ELSE FALSE
  END AS is_anomaly_pressure,

  CASE
    WHEN water_cut_pct IS NOT NULL AND prev_water_cut_pct IS NOT NULL
     AND water_cut_pct > 80 AND prev_water_cut_pct < 60
    THEN TRUE ELSE FALSE
  END AS is_water_cut_spike,

  CASE
    WHEN gas_oil_ratio IS NOT NULL
     AND baseline_gor  IS NOT NULL
     AND baseline_gor  > 0
     AND gas_oil_ratio > (baseline_gor * 3)
    THEN TRUE ELSE FALSE
  END AS is_gor_anomaly,

  current_timestamp() AS processed_ts

FROM enriched
"""

SQL_ROW_COUNT = f"SELECT COUNT(*) FROM {TARGET_TABLE}"

SQL_ANOMALY_SUMMARY = f"""
  SELECT
    well_id,
    date_year,
    COUNT(*)                                                    AS total_days,
    SUM(CASE WHEN is_anomaly_pressure THEN 1 ELSE 0 END)        AS pressure_anomalies,
    SUM(CASE WHEN is_water_cut_spike  THEN 1 ELSE 0 END)        AS water_cut_spikes,
    SUM(CASE WHEN is_gor_anomaly      THEN 1 ELSE 0 END)        AS gor_anomalies,
    SUM(CASE WHEN is_zero_prod_uptime THEN 1 ELSE 0 END)        AS zero_prod_days,
    ROUND(AVG(pressure_30d_avg), 1)                             AS avg_pressure_30d,
    ROUND(AVG(water_cut_30d_avg), 2)                            AS avg_water_cut_30d
  FROM {TARGET_TABLE}
  GROUP BY well_id, date_year
  ORDER BY well_id, date_year
"""


def run():
    print(f"\n{'='*60}")
    print("Gold Layer — Production Daily KPIs")
    print(f"{'='*60}")
    print(f"Source : {SOURCE_TABLE}")
    print(f"Target : {TARGET_TABLE}\n")

    with sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    ) as conn:
        with conn.cursor() as cur:

            print("[1/5] Creating schema claudecatalog.gold (if not exists)...")
            cur.execute(SQL_CREATE_SCHEMA)
            print("      OK")

            print(f"[2/5] Dropping existing table {TARGET_TABLE}...")
            cur.execute(SQL_DROP_TABLE)
            print("      OK")

            print(f"[3/5] Creating {TARGET_TABLE}...")
            print("      (CTAS with window functions — may take ~1-2 min)")
            cur.execute(SQL_CREATE_TABLE)
            print("      OK")

            print("[4/5] Verifying row count...")
            cur.execute(SQL_ROW_COUNT)
            total = cur.fetchone()[0]
            print(f"      Total rows : {total:,}")

            print("[5/5] Anomaly summary by well/year...")
            cur.execute(SQL_ANOMALY_SUMMARY)
            rows = cur.fetchall()
            print(f"\n{'Well':<8} {'Year':<6} {'Days':>5}  {'PressAnml':>10}  {'WCSpike':>8}  {'GORAnml':>8}  {'ZeroProd':>9}  {'P30d':>8}  {'WC30d':>7}")
            print("-" * 82)
            for row in rows:
                well, yr, days, pa, wcs, ga, zp, p30, wc30 = row
                p30_s  = f"{p30:.1f}"  if p30  is not None else "N/A"
                wc30_s = f"{wc30:.2f}" if wc30 is not None else "N/A"
                print(f"{str(well):<8} {str(yr):<6} {days:>5}  {int(pa):>10}  {int(wcs):>8}  {int(ga):>8}  {int(zp):>9}  {p30_s:>8}  {wc30_s:>7}")

    print(f"\nDone. {TARGET_TABLE} is ready.\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
