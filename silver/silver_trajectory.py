#!/usr/bin/env python3
"""
Silver Layer — WITSML Trajectory Data
Source : claudecatalog.bronze.raw_witsml_trajectory
Target : claudecatalog.silver.cleaned_trajectory (Delta, partitioned by well_id)
Run    : python silver/silver_trajectory.py

Transforms applied:
  - Explode trajectory_stations_json (JSON array) → one row per survey station
  - Extract md, incl, azi, tvd, dispNs, dispEw, dls from each station struct
  - All measurements cast to DOUBLE; NULL on parse failure
  - Quality flags: is_md_valid, is_incl_valid, is_azi_valid
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

SOURCE_TABLE = "claudecatalog.bronze.raw_witsml_trajectory"
TARGET_TABLE = "claudecatalog.silver.cleaned_trajectory"

SQL_CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS claudecatalog.silver"
SQL_DROP_TABLE    = f"DROP TABLE IF EXISTS {TARGET_TABLE}"

# WITSML trajectory station JSON structure (from TO_JSON on Spark XML parse):
#   [{"_uid":"1","md":{"_VALUE":"0.0","_uom":"m"},"incl":{"_VALUE":"0.0","_uom":"dega"}, ...}, ...]
#
# from_json() schema must match this shape. Fields absent in some versions → NULL (lenient parsing).
# Each measurement column is STRUCT<_VALUE: STRING, _uom: STRING>.
STATION_SCHEMA = """ARRAY<STRUCT<
  _uid: STRING,
  md:        STRUCT<_VALUE: STRING, _uom: STRING>,
  incl:      STRUCT<_VALUE: STRING, _uom: STRING>,
  azi:       STRUCT<_VALUE: STRING, _uom: STRING>,
  tvd:       STRUCT<_VALUE: STRING, _uom: STRING>,
  dispNs:    STRUCT<_VALUE: STRING, _uom: STRING>,
  dispEw:    STRUCT<_VALUE: STRING, _uom: STRING>,
  dls:       STRUCT<_VALUE: STRING, _uom: STRING>,
  rateTurn:  STRUCT<_VALUE: STRING, _uom: STRING>,
  rateBuild: STRUCT<_VALUE: STRING, _uom: STRING>
>>"""

SQL_CREATE_TABLE = f"""
CREATE TABLE {TARGET_TABLE}
USING DELTA
COMMENT 'Silver: one row per WITSML trajectory survey station. Exploded from bronze JSON array, measurements cast to DOUBLE.'
PARTITIONED BY (well_id)
AS
WITH parsed AS (
  SELECT
    trajectory_uid,
    uid_well,
    uid_wellbore,
    trajectory_name,
    name_well,
    name_wellbore,
    well_id,
    source_path,
    ingestion_ts,
    EXPLODE(
      from_json(trajectory_stations_json, '{STATION_SCHEMA}')
    ) AS station
  FROM {SOURCE_TABLE}
  WHERE trajectory_stations_json IS NOT NULL
    AND trajectory_stations_json != 'null'
)
SELECT
  -- Trajectory identifiers
  trajectory_uid,
  uid_well,
  uid_wellbore,
  trajectory_name,
  name_well,
  name_wellbore,
  well_id,
  station._uid                                    AS station_uid,

  -- Survey measurements (snake_case — new Silver columns)
  TRY_CAST(station.md._VALUE       AS DOUBLE)     AS md_m,
  station.md._uom                                 AS md_uom,
  TRY_CAST(station.incl._VALUE     AS DOUBLE)     AS incl_deg,
  TRY_CAST(station.azi._VALUE      AS DOUBLE)     AS azi_deg,
  TRY_CAST(station.tvd._VALUE      AS DOUBLE)     AS tvd_m,
  TRY_CAST(station.dispNs._VALUE   AS DOUBLE)     AS disp_ns_m,
  TRY_CAST(station.dispEw._VALUE   AS DOUBLE)     AS disp_ew_m,
  TRY_CAST(station.dls._VALUE      AS DOUBLE)     AS dls_deg_per_30m,
  TRY_CAST(station.rateTurn._VALUE AS DOUBLE)     AS rate_turn,
  TRY_CAST(station.rateBuild._VALUE AS DOUBLE)    AS rate_build,

  -- Quality flags
  CASE
    WHEN TRY_CAST(station.md._VALUE AS DOUBLE) IS NOT NULL
     AND TRY_CAST(station.md._VALUE AS DOUBLE) >= 0
    THEN TRUE ELSE FALSE
  END                                             AS is_md_valid,

  CASE
    WHEN TRY_CAST(station.incl._VALUE AS DOUBLE) IS NOT NULL
     AND TRY_CAST(station.incl._VALUE AS DOUBLE) BETWEEN 0 AND 180
    THEN TRUE ELSE FALSE
  END                                             AS is_incl_valid,

  CASE
    WHEN TRY_CAST(station.azi._VALUE AS DOUBLE) IS NOT NULL
     AND TRY_CAST(station.azi._VALUE AS DOUBLE) BETWEEN 0 AND 360
    THEN TRUE ELSE FALSE
  END                                             AS is_azi_valid,

  -- Metadata
  source_path,
  ingestion_ts,
  current_timestamp()                             AS processed_ts

FROM parsed
WHERE station IS NOT NULL
"""

SQL_ROW_COUNT       = f"SELECT COUNT(*) FROM {TARGET_TABLE}"
SQL_WELL_SUMMARY    = f"""
  SELECT
    well_id,
    COUNT(DISTINCT trajectory_uid)                      AS trajectories,
    COUNT(*)                                            AS total_stations,
    ROUND(MIN(md_m), 1)                                 AS min_md_m,
    ROUND(MAX(md_m), 1)                                 AS max_md_m,
    ROUND(MAX(tvd_m), 1)                                AS max_tvd_m,
    SUM(CASE WHEN NOT is_md_valid   THEN 1 ELSE 0 END)  AS invalid_md,
    SUM(CASE WHEN NOT is_incl_valid THEN 1 ELSE 0 END)  AS invalid_incl,
    SUM(CASE WHEN NOT is_azi_valid  THEN 1 ELSE 0 END)  AS invalid_azi
  FROM {TARGET_TABLE}
  GROUP BY well_id
  ORDER BY well_id
"""


def run():
    print(f"\n{'='*60}")
    print("Silver Layer — WITSML Trajectory Data")
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
            print("      (Exploding JSON array + casting — may take ~1 min)")
            cur.execute(SQL_CREATE_TABLE)
            print("      OK")

            print("[4/5] Verifying row counts...")
            cur.execute(SQL_ROW_COUNT)
            total = cur.fetchone()[0]
            print(f"      Total survey stations : {total:,}")

            print("[5/5] Quality summary by well...")
            cur.execute(SQL_WELL_SUMMARY)
            rows = cur.fetchall()
            print(f"\n{'Well':<8} {'Trajs':>6}  {'Stations':>9}  {'MinMD':>8}  {'MaxMD':>8}  {'MaxTVD':>8}  {'!MD':>5}  {'!Inc':>5}  {'!Azi':>5}")
            print("-" * 80)
            for row in rows:
                well_id, trajs, stations, min_md, max_md, max_tvd, bad_md, bad_incl, bad_azi = row
                min_md_s  = f"{min_md:.1f}"  if min_md  is not None else "N/A"
                max_md_s  = f"{max_md:.1f}"  if max_md  is not None else "N/A"
                max_tvd_s = f"{max_tvd:.1f}" if max_tvd is not None else "N/A"
                print(f"{str(well_id):<8} {int(trajs):>6}  {int(stations):>9}  {min_md_s:>8}  {max_md_s:>8}  {max_tvd_s:>8}  {int(bad_md):>5}  {int(bad_incl):>5}  {int(bad_azi):>5}")

    print(f"\nDone. {TARGET_TABLE} is ready.\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
