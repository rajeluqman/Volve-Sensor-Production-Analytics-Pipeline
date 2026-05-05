#!/usr/bin/env python3
"""
Silver Layer — Production Data
Source : claudecatalog.bronze.raw_production
Target : claudecatalog.silver.cleaned_production (Delta, partitioned by date_year + well_id)
Run    : python silver/silver_production.py

Transforms applied:
  - DATEPRD → proper DATE type
  - All numeric columns → DOUBLE (TRY_CAST; unparseable = NULL)
  - Derived: water_cut_pct, gas_oil_ratio
  - Quality flags: is_zero_prod_uptime, is_pressure_valid
  - Dedup: keep latest ingestion_ts per (WELL_BORE_CODE, DATEPRD)
  - Drop rows where DATEPRD or WELL_BORE_CODE is NULL
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

SOURCE_TABLE = "claudecatalog.bronze.raw_production"
TARGET_TABLE = "claudecatalog.silver.cleaned_production"

SQL_CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS claudecatalog.silver"
SQL_DROP_TABLE    = f"DROP TABLE IF EXISTS {TARGET_TABLE}"

# Silver production: type-cast source columns (UPPERCASE preserved), add derived snake_case columns.
# TRY_CAST returns NULL on parse failure — safe for downstream DQ checks.
# Dedup window: latest ingestion_ts wins per (WELL_BORE_CODE, DATEPRD).
SQL_CREATE_TABLE = f"""
CREATE TABLE {TARGET_TABLE}
USING DELTA
COMMENT 'Silver: cleaned production data. Types cast, derived KPIs added, duplicates removed.'
PARTITIONED BY (date_year, well_id)
AS
WITH deduped AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY WELL_BORE_CODE, DATEPRD
      ORDER BY ingestion_ts DESC
    ) AS _rn
  FROM {SOURCE_TABLE}
  WHERE DATEPRD IS NOT NULL
    AND WELL_BORE_CODE IS NOT NULL
    AND well_id IN ('F-1', 'F-11', 'F-12')
),
casted AS (
  SELECT
    -- Dates
    TO_DATE(DATEPRD, 'dd-MMM-yy')                AS DATEPRD,

    -- Well identifiers (source strings, preserved)
    WELL_BORE_CODE,
    NPD_WELL_BORE_CODE,
    NPD_WELL_BORE_NAME,
    NPD_FIELD_CODE,
    NPD_FIELD_NAME,
    NPD_FACILITY_CODE,
    NPD_FACILITY_NAME,

    -- Operational metrics (cast to DOUBLE)
    TRY_CAST(ON_STREAM_HRS           AS DOUBLE)  AS ON_STREAM_HRS,
    TRY_CAST(AVG_DOWNHOLE_PRESSURE   AS DOUBLE)  AS AVG_DOWNHOLE_PRESSURE,
    TRY_CAST(AVG_DOWNHOLE_TEMPERATURE AS DOUBLE) AS AVG_DOWNHOLE_TEMPERATURE,
    TRY_CAST(AVG_DP_TUBING           AS DOUBLE)  AS AVG_DP_TUBING,
    TRY_CAST(AVG_ANNULUS_PRESS       AS DOUBLE)  AS AVG_ANNULUS_PRESS,
    TRY_CAST(AVG_CHOKE_SIZE_P        AS DOUBLE)  AS AVG_CHOKE_SIZE_P,
    AVG_CHOKE_UOM,
    TRY_CAST(AVG_WHP_P               AS DOUBLE)  AS AVG_WHP_P,
    TRY_CAST(AVG_WHT_P               AS DOUBLE)  AS AVG_WHT_P,
    TRY_CAST(DP_CHOKE_SIZE           AS DOUBLE)  AS DP_CHOKE_SIZE,

    -- Production volumes (cast to DOUBLE)
    TRY_CAST(BORE_OIL_VOL  AS DOUBLE)            AS BORE_OIL_VOL,
    TRY_CAST(BORE_GAS_VOL  AS DOUBLE)            AS BORE_GAS_VOL,
    TRY_CAST(BORE_WAT_VOL  AS DOUBLE)            AS BORE_WAT_VOL,
    TRY_CAST(BORE_WI_VOL   AS DOUBLE)            AS BORE_WI_VOL,

    -- Categorical
    FLOW_KIND,
    WELL_TYPE,

    -- Partition / identifier cols already clean from Bronze
    well_id,
    date_year,

    -- Bronze metadata passthrough
    ingestion_ts,
    source_system,
    source_file

  FROM deduped
  WHERE _rn = 1
    AND TO_DATE(DATEPRD, 'dd-MMM-yy') IS NOT NULL
)
SELECT
  *,

  -- Derived KPIs (snake_case — new columns not in source)
  CASE
    WHEN (BORE_OIL_VOL + BORE_WAT_VOL) > 0
    THEN BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100.0
    ELSE NULL
  END                                             AS water_cut_pct,

  CASE
    WHEN BORE_OIL_VOL > 0
    THEN BORE_GAS_VOL / BORE_OIL_VOL
    ELSE NULL
  END                                             AS gas_oil_ratio,

  -- Quality flags
  CASE
    WHEN BORE_OIL_VOL IS NOT NULL
     AND ON_STREAM_HRS IS NOT NULL
     AND BORE_OIL_VOL = 0
     AND ON_STREAM_HRS > 0
    THEN TRUE
    ELSE FALSE
  END                                             AS is_zero_prod_uptime,

  -- Pressure valid: 0–10000 psi; NULL pressure treated as invalid
  CASE
    WHEN AVG_DOWNHOLE_PRESSURE IS NOT NULL
     AND AVG_DOWNHOLE_PRESSURE >= 0
     AND AVG_DOWNHOLE_PRESSURE <= 10000
    THEN TRUE
    ELSE FALSE
  END                                             AS is_pressure_valid,

  current_timestamp()                             AS processed_ts

FROM casted
"""

SQL_ROW_COUNT   = f"SELECT COUNT(*) FROM {TARGET_TABLE}"
SQL_WELL_COUNTS = f"""
  SELECT well_id, date_year,
         COUNT(*)                                          AS rows,
         ROUND(AVG(water_cut_pct), 2)                     AS avg_water_cut_pct,
         ROUND(AVG(gas_oil_ratio), 4)                     AS avg_gor,
         SUM(CASE WHEN is_zero_prod_uptime THEN 1 ELSE 0 END) AS zero_prod_days,
         SUM(CASE WHEN NOT is_pressure_valid THEN 1 ELSE 0 END) AS invalid_pressure_rows
  FROM {TARGET_TABLE}
  GROUP BY well_id, date_year
  ORDER BY well_id, date_year
  LIMIT 30
"""
SQL_NULL_CHECK  = f"""
  SELECT
    SUM(CASE WHEN DATEPRD IS NULL THEN 1 ELSE 0 END)              AS null_date,
    SUM(CASE WHEN BORE_OIL_VOL IS NULL THEN 1 ELSE 0 END)         AS null_oil_vol,
    SUM(CASE WHEN AVG_DOWNHOLE_PRESSURE IS NULL THEN 1 ELSE 0 END) AS null_pressure
  FROM {TARGET_TABLE}
"""


def run():
    print(f"\n{'='*60}")
    print("Silver Layer — Production Data")
    print(f"{'='*60}")
    print(f"Source : {SOURCE_TABLE}")
    print(f"Target : {TARGET_TABLE}\n")

    with sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    ) as conn:
        with conn.cursor() as cur:

            print("[1/5] Creating schema claudecatalog.silver (if not exists)...")
            cur.execute(SQL_CREATE_SCHEMA)
            print("      OK")

            print(f"[2/5] Dropping existing table {TARGET_TABLE}...")
            cur.execute(SQL_DROP_TABLE)
            print("      OK")

            print(f"[3/5] Creating {TARGET_TABLE}...")
            print("      (CTAS with dedup + type casting — may take ~1 min)")
            cur.execute(SQL_CREATE_TABLE)
            print("      OK")

            print("[4/5] Verifying row counts...")
            cur.execute(SQL_ROW_COUNT)
            total = cur.fetchone()[0]
            print(f"      Total rows : {total:,}")

            print("[5/5] Quality summary by well/year...")
            cur.execute(SQL_WELL_COUNTS)
            rows = cur.fetchall()
            print(f"\n{'Well':<8} {'Year':<6} {'Rows':>6}  {'AvgWC%':>8}  {'AvgGOR':>8}  {'ZeroProd':>9}  {'BadPress':>9}")
            print("-" * 70)
            for row in rows:
                well_id, date_year, count, avg_wc, avg_gor, zp, bp = row
                avg_wc_str  = f"{avg_wc:.2f}"  if avg_wc  is not None else "N/A"
                avg_gor_str = f"{avg_gor:.4f}" if avg_gor is not None else "N/A"
                print(f"{str(well_id):<8} {str(date_year):<6} {count:>6}  {avg_wc_str:>8}  {avg_gor_str:>8}  {int(zp):>9}  {int(bp):>9}")

            print("\n      NULL checks:")
            cur.execute(SQL_NULL_CHECK)
            null_row = cur.fetchone()
            print(f"      null_date={null_row[0]}  null_oil_vol={null_row[1]}  null_pressure={null_row[2]}")

    print(f"\nDone. {TARGET_TABLE} is ready.\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
