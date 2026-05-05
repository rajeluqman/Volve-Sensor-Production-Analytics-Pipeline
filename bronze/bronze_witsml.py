#!/usr/bin/env python3
"""
Bronze Layer — WITSML Realtime Drilling Data (Trajectory)
Source : /Volumes/equinor_asa_volve_data_village/public/volve/WITSML Realtime drilling data/
Target : claudecatalog.bronze.raw_witsml_trajectory (Delta table, partitioned by well_id)
Run    : python bronze/bronze_witsml.py

Strategy:
  1. Discover all well folders for F-1, F-11, F-12
  2. Within each well folder, list numbered wellbore subdirectories (1/, 2/, etc.)
  3. Check which numbered subdirs have a trajectory/ folder
  4. read_files(format='xml', rowTag='trajectory') from those paths
  5. Bronze stores raw struct (trajectoryStation is nested array — Silver will explode)
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from databricks import sql

load_dotenv(Path(__file__).parent.parent / ".env")

HOST        = os.environ["DATABRICKS_HOST"].replace("https://", "")
HTTP_PATH   = os.environ["DATABRICKS_HTTP_PATH"]
TOKEN       = os.environ["DATABRICKS_TOKEN"]

WITSML_VOLUME = "/Volumes/equinor_asa_volve_data_village/public/volve/WITSML Realtime drilling data"
TARGET_TABLE  = "claudecatalog.bronze.raw_witsml_trajectory"
WELLS_IN_SCOPE = ["F-1", "F-11", "F-12"]


def discover_well_folders(cur) -> dict[str, list[str]]:
    """Return {well_id: [folder1, folder2, ...]} for the 3 target wells."""
    cur.execute(f"LIST '{WITSML_VOLUME}'")
    rows = cur.fetchall()

    well_folders: dict[str, list[str]] = {w: [] for w in WELLS_IN_SCOPE}
    for row in rows:
        path = str(row.path).rstrip("/")
        last = path.split("/")[-1]
        if "." in last:
            continue  # skip files

        for well_id in WELLS_IN_SCOPE:
            well_num = well_id.split("-")[1]
            pattern  = re.compile(rf'\bF-{well_num}\b', re.IGNORECASE)
            if pattern.search(path):
                well_folders[well_id].append(path + "/")
                break

    return {k: v for k, v in well_folders.items() if v}


def discover_trajectory_paths(cur, well_folders: dict[str, list[str]]) -> dict[str, list[str]]:
    """
    For each well folder, list numbered wellbore subdirectories and check which
    contain a trajectory/ subfolder. Return {well_id: [trajectory_path1, ...]}.
    """
    trajectory_paths: dict[str, list[str]] = {}

    for well_id, folders in well_folders.items():
        trajectory_paths[well_id] = []

        for well_folder in folders:
            # List contents of the well folder
            cur.execute(f"LIST '{well_folder}'")
            items = cur.fetchall()

            for item in items:
                item_name = item.name.rstrip("/")
                # Numbered wellbore subdirectories (1, 2, 3, ...)
                if item.size == 0 and item_name.isdigit():
                    wellbore_path = item.path
                    # Check if trajectory/ exists inside this wellbore dir
                    cur.execute(f"LIST '{wellbore_path}'")
                    wellbore_contents = cur.fetchall()
                    sub_names = {r.name.rstrip("/") for r in wellbore_contents}
                    if "trajectory" in sub_names:
                        traj_path = wellbore_path + "trajectory/"
                        trajectory_paths[well_id].append(traj_path)

    return {k: v for k, v in trajectory_paths.items() if v}


def select_for_path(well_id: str, traj_path: str) -> str:
    # Only mandatory WITSML trajectory fields are selected as columns.
    # Optional fields (serviceCompany, aziRef, mdMn, etc.) vary per WITSML version/file
    # and are NOT selected individually to avoid UNION ALL schema mismatch.
    # trajectoryStation → TO_JSON to handle differing nested struct schemas.
    return f"""  SELECT
    _uid                                AS trajectory_uid,
    _uidWell                            AS uid_well,
    _uidWellbore                        AS uid_wellbore,
    name                                AS trajectory_name,
    nameWell                            AS name_well,
    nameWellbore                        AS name_wellbore,
    TO_JSON(trajectoryStation)          AS trajectory_stations_json,
    '{well_id}'                         AS well_id,
    '{traj_path}'                       AS source_path,
    current_timestamp()                 AS ingestion_ts,
    'witsml_trajectory'                 AS source_system
  FROM read_files(
    '{traj_path}',
    format => 'xml',
    rowTag => 'trajectory'
  )"""


def build_create_table_sql(trajectory_paths: dict[str, list[str]]) -> str:
    if not any(trajectory_paths.values()):
        raise ValueError("No trajectory paths found for any well.")

    all_selects = []
    for well_id, paths in trajectory_paths.items():
        for path in paths:
            all_selects.append(select_for_path(well_id, path))

    union_body = "\nUNION ALL\n".join(all_selects)

    return f"""
CREATE TABLE {TARGET_TABLE}
USING DELTA
COMMENT 'Bronze: raw WITSML trajectory data. One row per trajectory. trajectory_stations is nested array — Silver will explode and flatten.'
PARTITIONED BY (well_id)
AS
{union_body}
"""


def run():
    print(f"\n{'='*60}")
    print("Bronze Layer — WITSML Trajectory Data")
    print(f"{'='*60}")
    print(f"Source : {WITSML_VOLUME}")
    print(f"Target : {TARGET_TABLE}")
    print(f"Wells  : {WELLS_IN_SCOPE}\n")

    with sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    ) as conn:
        with conn.cursor() as cur:

            print("[1/5] Ensuring schema claudecatalog.bronze exists...")
            cur.execute("CREATE SCHEMA IF NOT EXISTS claudecatalog.bronze")
            print("      OK")

            print("[2/5] Discovering WITSML well folders...")
            well_folders = discover_well_folders(cur)
            if not well_folders:
                print("      ERROR: No well folders found.")
                sys.exit(1)
            total_folders = sum(len(v) for v in well_folders.values())
            print(f"      Found {total_folders} well folders across {len(well_folders)} wells")

            print("[3/5] Discovering trajectory subdirectories...")
            trajectory_paths = discover_trajectory_paths(cur, well_folders)
            if not any(trajectory_paths.values()):
                print("      ERROR: No trajectory paths found.")
                sys.exit(1)
            for well_id, paths in trajectory_paths.items():
                for p in paths:
                    print(f"      {well_id:6s} → {'/'.join(p.split('/')[-4:])}")

            print(f"\n[4/5] Dropping existing table {TARGET_TABLE} (if exists)...")
            cur.execute(f"DROP TABLE IF EXISTS {TARGET_TABLE}")
            print("      OK")

            print(f"[5/6] Creating {TARGET_TABLE}...")
            print("      (XML parsing across all trajectory files)")
            create_sql = build_create_table_sql(trajectory_paths)
            cur.execute(create_sql)
            print("      OK")

            print("[6/6] Verifying results...")
            cur.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}")
            total = cur.fetchone()[0]
            print(f"      Total trajectories : {total:,}")

            cur.execute(f"""
                SELECT well_id, name_well, name_wellbore, trajectory_uid, source_path
                FROM {TARGET_TABLE}
                ORDER BY well_id, name_wellbore
            """)
            rows = cur.fetchall()
            print(f"\n{'Well':<8} {'WellName':<25} {'Wellbore':<20} {'UID':<38}")
            print("-" * 95)
            for row in rows:
                well_id, name_well, name_wellbore, traj_uid, source_path = row
                name_well_str = str(name_well or '')[:24]
                name_wb_str   = str(name_wellbore or '')[:19]
                uid_str       = str(traj_uid or '')[:37]
                print(f"{str(well_id):<8} {name_well_str:<25} {name_wb_str:<20} {uid_str:<38}")

    print(f"\nDone. Table {TARGET_TABLE} is ready.")
    print("Next: Silver layer will explode trajectory_stations → one row per survey station.\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
