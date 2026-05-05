#!/usr/bin/env python3
"""
Bronze Layer — Production Data
Source : /Volumes/equinor_asa_volve_data_village/public/volve/Production_data/Volve production data.xlsx
Target : claudecatalog.bronze.raw_production (Delta table, partitioned by date_year + well_id)
Run    : python bronze/bronze_production.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from databricks import sql

load_dotenv(Path(__file__).parent.parent / ".env")

HOST        = os.environ["DATABRICKS_HOST"].replace("https://", "")
HTTP_PATH   = os.environ["DATABRICKS_HTTP_PATH"]
TOKEN       = os.environ["DATABRICKS_TOKEN"]

VOLUME_PATH  = "/Volumes/equinor_asa_volve_data_village/public/volve/Production_data/Volve production data.xlsx"
TARGET_TABLE = "claudecatalog.bronze.raw_production"
WELLS_IN_SCOPE = ("F-1", "F-11", "F-12")

SQL_CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS claudecatalog.bronze"

SQL_DROP_TABLE = f"DROP TABLE IF EXISTS {TARGET_TABLE}"

# NOTE: Databricks Excel reader via read_files() does not honour 'header => true' in SQL Warehouse —
# all columns come as _c0.._c23. We skip the literal header row (WHERE _c0 != 'DATEPRD')
# and alias each _cN to the source column name explicitly.
SQL_CREATE_TABLE = f"""
CREATE TABLE {TARGET_TABLE}
USING DELTA
COMMENT 'Bronze: raw production data from Equinor Volve dataset. One record per well per report date.'
PARTITIONED BY (date_year, well_id)
AS
SELECT
  _c0   AS DATEPRD,
  _c1   AS WELL_BORE_CODE,
  _c2   AS NPD_WELL_BORE_CODE,
  _c3   AS NPD_WELL_BORE_NAME,
  _c4   AS NPD_FIELD_CODE,
  _c5   AS NPD_FIELD_NAME,
  _c6   AS NPD_FACILITY_CODE,
  _c7   AS NPD_FACILITY_NAME,
  _c8   AS ON_STREAM_HRS,
  _c9   AS AVG_DOWNHOLE_PRESSURE,
  _c10  AS AVG_DOWNHOLE_TEMPERATURE,
  _c11  AS AVG_DP_TUBING,
  _c12  AS AVG_ANNULUS_PRESS,
  _c13  AS AVG_CHOKE_SIZE_P,
  _c14  AS AVG_CHOKE_UOM,
  _c15  AS AVG_WHP_P,
  _c16  AS AVG_WHT_P,
  _c17  AS DP_CHOKE_SIZE,
  _c18  AS BORE_OIL_VOL,
  _c19  AS BORE_GAS_VOL,
  _c20  AS BORE_WAT_VOL,
  _c21  AS BORE_WI_VOL,
  _c22  AS FLOW_KIND,
  _c23  AS WELL_TYPE,
  REGEXP_EXTRACT(_c1, 'F-[0-9]+', 0)  AS well_id,
  YEAR(TO_DATE(_c0, 'dd-MMM-yy'))      AS date_year,
  current_timestamp()                  AS ingestion_ts,
  'equinor_volve_volume'               AS source_system,
  '{VOLUME_PATH}'                      AS source_file
FROM read_files(
  '{VOLUME_PATH}',
  format => 'excel'
)
WHERE _c0 != 'DATEPRD'
  AND REGEXP_EXTRACT(_c1, 'F-[0-9]+', 0) IN ('F-1', 'F-11', 'F-12')
"""

SQL_ROW_COUNT   = f"SELECT COUNT(*) FROM {TARGET_TABLE}"
SQL_WELL_COUNTS = f"""
  SELECT well_id, date_year, COUNT(*) AS row_count
  FROM {TARGET_TABLE}
  GROUP BY well_id, date_year
  ORDER BY well_id, date_year
  LIMIT 30
"""


def run():
    print(f"\n{'='*60}")
    print("Bronze Layer — Production Data")
    print(f"{'='*60}")
    print(f"Source : {VOLUME_PATH}")
    print(f"Target : {TARGET_TABLE}")
    print(f"Wells  : {WELLS_IN_SCOPE}\n")

    with sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    ) as conn:
        with conn.cursor() as cur:

            print("[1/4] Creating schema claudecatalog.bronze (if not exists)...")
            cur.execute(SQL_CREATE_SCHEMA)
            print("      OK")

            print(f"[2/4] Dropping existing table {TARGET_TABLE} (if exists)...")
            cur.execute(SQL_DROP_TABLE)
            print("      OK")

            print(f"[3/4] Creating {TARGET_TABLE} from Excel volume...")
            print("      (This may take 1-2 minutes on first run)")
            cur.execute(SQL_CREATE_TABLE)
            print("      OK")

            print("[4/4] Verifying row counts...")
            cur.execute(SQL_ROW_COUNT)
            total = cur.fetchone()[0]
            print(f"      Total rows : {total:,}")

            cur.execute(SQL_WELL_COUNTS)
            rows = cur.fetchall()
            print(f"\n{'Well':<8} {'Year':<6} {'Rows':>8}")
            print("-" * 25)
            for well_id, date_year, count in rows:
                print(f"{str(well_id):<8} {str(date_year):<6} {count:>8,}")

    print(f"\nDone. Table {TARGET_TABLE} is ready.\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
