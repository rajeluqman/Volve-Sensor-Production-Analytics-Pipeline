#!/usr/bin/env python3
"""
Phase 7 — Data Quality Orchestrator
Runs all 4 GE-style suites against Databricks SQL Warehouse.
Writes per-run results to claudecatalog.silver.dq_results.

Usage:
  python data_quality/run_dq.py                             # all suites
  python data_quality/run_dq.py --suite bronze_production_suite
  python data_quality/run_dq.py --suite silver_production_suite,gold_feature_suite

Exit codes:
  0 — all suites passed (>= 95% expectations met)
  1 — one or more suites failed
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from databricks import sql
from dotenv import load_dotenv

# Allow running from repo root or from data_quality/
sys.path.insert(0, str(Path(__file__).parent))

from suites.bronze_production_suite import run as run_bronze
from suites.silver_production_suite import run as run_silver_prod
from suites.silver_witsml_suite import run as run_silver_witsml
from suites.gold_feature_suite import run as run_gold
from suites.base import SuiteResult

load_dotenv(Path(__file__).parent.parent / ".env")

HOST      = os.environ["DATABRICKS_HOST"].replace("https://", "")
HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
TOKEN     = os.environ["DATABRICKS_TOKEN"]

ALL_SUITES = {
    "bronze_production_suite": run_bronze,
    "silver_production_suite": run_silver_prod,
    "silver_witsml_suite":     run_silver_witsml,
    "gold_feature_suite":      run_gold,
}

RESULTS_TABLE = "claudecatalog.silver.dq_results"

SQL_CREATE_RESULTS_TABLE = f"""
CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
    run_ts          TIMESTAMP,
    suite_name      STRING,
    table_name      STRING,
    row_count       BIGINT,
    n_expectations  INT,
    n_passed        INT,
    n_failed        INT,
    pass_rate       DOUBLE,
    suite_success   BOOLEAN,
    expectations_json STRING
)
USING DELTA
COMMENT 'Data quality run history. One row per suite per run. Written by data_quality/run_dq.py.'
"""


def _write_results(cursor, results: list[SuiteResult]) -> None:
    cursor.execute("CREATE SCHEMA IF NOT EXISTS claudecatalog.silver")
    cursor.execute(SQL_CREATE_RESULTS_TABLE)

    for r in results:
        expectations_json = json.dumps([
            {
                "name":         e.name,
                "passed":       e.passed,
                "details":      e.details,
                "actual_value": e.actual_value,
                "threshold":    e.threshold,
            }
            for e in r.expectations
        ])
        cursor.execute(
            f"""
            INSERT INTO {RESULTS_TABLE}
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r.run_ts,
                r.suite_name,
                r.table,
                r.row_count,
                r.n_total,
                r.n_passed,
                r.n_failed,
                round(r.pass_rate, 6),
                r.success,
                expectations_json,
            ),
        )


def _print_report(results: list[SuiteResult]) -> None:
    width = 70
    print("\n" + "=" * width)
    print("  VOLVE DATA QUALITY REPORT")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * width)

    for r in results:
        status = "PASS" if r.success else "FAIL"
        bar = "#" * int(r.pass_rate * 20) + "-" * (20 - int(r.pass_rate * 20))
        print(f"\n  [{status}]  {r.suite_name}")
        print(f"         Table     : {r.table}")
        print(f"         Row count : {r.row_count:,}")
        print(f"         Pass rate : {r.pass_rate * 100:5.1f}%  [{bar}]  "
              f"({r.n_passed}/{r.n_total} expectations)")

        for e in r.expectations:
            icon = "✓" if e.passed else "✗"
            print(f"           {icon}  {e.name}")
            print(f"              {e.details}")

    print("\n" + "=" * width)
    all_pass = all(r.success for r in results)
    if all_pass:
        print("  OVERALL: ALL SUITES PASSED")
    else:
        failed = [r.suite_name for r in results if not r.success]
        print(f"  OVERALL: FAILED — {', '.join(failed)}")
    print("=" * width + "\n")


def _parse_args():
    parser = argparse.ArgumentParser(description="Volve DQ suite runner")
    parser.add_argument(
        "--suite",
        default=None,
        help="Comma-separated suite names to run (default: all)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    if args.suite:
        selected = [s.strip() for s in args.suite.split(",")]
        unknown = [s for s in selected if s not in ALL_SUITES]
        if unknown:
            print(f"ERROR: unknown suite(s): {unknown}")
            print(f"Available: {list(ALL_SUITES.keys())}")
            sys.exit(1)
        suites_to_run = {k: ALL_SUITES[k] for k in selected}
    else:
        suites_to_run = ALL_SUITES

    print(f"\nConnecting to Databricks SQL Warehouse...")
    with sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    ) as conn:
        with conn.cursor() as cursor:
            results = []
            for name, run_fn in suites_to_run.items():
                print(f"  Running {name}...")
                try:
                    result = run_fn(cursor)
                    results.append(result)
                    status = "PASS" if result.success else "FAIL"
                    print(f"    [{status}] {result.pass_rate * 100:.1f}%  "
                          f"({result.n_passed}/{result.n_total} expectations)")
                except Exception as exc:
                    print(f"    [ERROR] {name}: {exc}")
                    raise

            print(f"\nWriting results to {RESULTS_TABLE}...")
            _write_results(cursor, results)

    _print_report(results)

    if not all(r.success for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
