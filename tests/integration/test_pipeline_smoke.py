"""
Integration smoke tests — Volve pipeline end-to-end connectivity check.

These tests verify that:
  1. Databricks SQL Warehouse is reachable and key Delta tables exist with data
  2. Snowflake SERVING layer is reachable and key views are queryable

All tests are skipped automatically when credentials are absent (CI / no .env).

Run:
  pytest tests/integration/ -v -m integration
  pytest tests/integration/ -v          # same — all tests here are integration
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")


# ---------------------------------------------------------------------------
# Databricks smoke tests
# ---------------------------------------------------------------------------

DATABRICKS_TABLES = [
    ("claudecatalog.bronze.raw_production",        4_000),   # 4,967 rows loaded
    ("claudecatalog.silver.cleaned_production",    4_000),
    ("claudecatalog.gold.production_daily",        4_000),
    ("claudecatalog.gold.ml_feature_store",        1_000),
]

DATABRICKS_WELLS = ["F-1", "F-11", "F-12"]


@pytest.mark.integration
class TestDatabricksConnectivity:
    """Verify Databricks SQL Warehouse is reachable and tables have expected data."""

    @pytest.fixture(scope="class", autouse=True)
    def conn(self, databricks_env):
        from databricks import sql
        with sql.connect(
            server_hostname=databricks_env["host"],
            http_path=databricks_env["http_path"],
            access_token=databricks_env["token"],
        ) as connection:
            self._conn = connection
            yield connection

    def _query_one(self, sql_text):
        with self._conn.cursor() as cur:
            cur.execute(sql_text)
            return cur.fetchone()

    def _query_all(self, sql_text):
        with self._conn.cursor() as cur:
            cur.execute(sql_text)
            return cur.fetchall()

    @pytest.mark.parametrize("table,min_rows", DATABRICKS_TABLES)
    def test_table_row_count(self, table, min_rows, databricks_env):
        row = self._query_one(f"SELECT COUNT(*) FROM {table}")
        count = row[0]
        assert count >= min_rows, (
            f"{table} has only {count:,} rows — expected >= {min_rows:,}"
        )

    def test_silver_no_null_dateprd(self, databricks_env):
        row = self._query_one(
            "SELECT COUNT(*) FROM claudecatalog.silver.cleaned_production "
            "WHERE DATEPRD IS NULL"
        )
        assert row[0] == 0, f"Silver has {row[0]} rows with NULL DATEPRD"

    def test_silver_wells_present(self, databricks_env):
        rows = self._query_all(
            "SELECT DISTINCT well_id FROM claudecatalog.silver.cleaned_production "
            "ORDER BY well_id"
        )
        found = [r[0] for r in rows]
        for well in DATABRICKS_WELLS:
            assert well in found, f"Well {well} missing from silver.cleaned_production"

    def test_silver_water_cut_range(self, databricks_env):
        row = self._query_one(
            "SELECT COUNT(*) FROM claudecatalog.silver.cleaned_production "
            "WHERE water_cut_pct IS NOT NULL AND (water_cut_pct < 0 OR water_cut_pct > 100)"
        )
        assert row[0] == 0, f"{row[0]} silver rows have water_cut_pct outside [0, 100]"

    def test_gold_anomaly_flags_exist(self, databricks_env):
        row = self._query_one(
            "SELECT COUNT(*) FROM claudecatalog.gold.production_daily "
            "WHERE is_anomaly_pressure IS NOT NULL"
        )
        assert row[0] > 0, "No rows with is_anomaly_pressure in gold.production_daily"

    def test_gold_pressure_delta_non_negative(self, databricks_env):
        row = self._query_one(
            "SELECT COUNT(*) FROM claudecatalog.gold.production_daily "
            "WHERE pressure_delta_24h < 0"
        )
        assert row[0] == 0, f"{row[0]} gold rows have negative pressure_delta_24h"

    def test_ml_feature_store_target_columns(self, databricks_env):
        row = self._query_one(
            "SELECT COUNT(*) FROM claudecatalog.gold.ml_feature_store "
            "WHERE next_day_pressure IS NOT NULL"
        )
        assert row[0] > 0, "ml_feature_store has no rows with next_day_pressure"


# ---------------------------------------------------------------------------
# Snowflake smoke tests
# ---------------------------------------------------------------------------

SNOWFLAKE_VIEWS = [
    "vw_daily_production_kpis",
    "vw_anomaly_alerts",
    "vw_production_trends",
    "vw_well_comparison",
]


@pytest.mark.integration
class TestSnowflakeConnectivity:
    """Verify Snowflake SERVING layer is reachable and views return data."""

    @pytest.fixture(scope="class", autouse=True)
    def conn(self, snowflake_env):
        import snowflake.connector
        con = snowflake.connector.connect(
            account=snowflake_env["SNOWFLAKE_ACCOUNT"],
            user=snowflake_env["SNOWFLAKE_USER"],
            password=snowflake_env["SNOWFLAKE_PASSWORD"],
            database=snowflake_env["SNOWFLAKE_DATABASE"],
            schema=snowflake_env["SNOWFLAKE_SCHEMA"],
            warehouse=snowflake_env["SNOWFLAKE_WAREHOUSE"],
        )
        self._conn = con
        yield con
        con.close()

    def _query_one(self, sql_text):
        cur = self._conn.cursor()
        cur.execute(sql_text)
        return cur.fetchone()

    def test_staging_table_row_count(self, snowflake_env):
        row = self._query_one("SELECT COUNT(*) FROM VOLVE_DB.SERVING.production_daily")
        assert row[0] >= 4_000, (
            f"Snowflake production_daily has {row[0]:,} rows — expected >= 4,000"
        )

    @pytest.mark.parametrize("view", SNOWFLAKE_VIEWS)
    def test_view_returns_rows(self, view, snowflake_env):
        row = self._query_one(f"SELECT COUNT(*) FROM VOLVE_DB.SERVING.{view}")
        assert row[0] > 0, f"Snowflake view {view} returned 0 rows"

    def test_anomaly_alerts_severity_values(self, snowflake_env):
        cur = self._conn.cursor()
        cur.execute(
            "SELECT DISTINCT severity FROM VOLVE_DB.SERVING.vw_anomaly_alerts "
            "ORDER BY severity"
        )
        severities = {r[0] for r in cur.fetchall()}
        valid = {"CRITICAL", "HIGH", "MEDIUM"}
        unexpected = severities - valid
        assert not unexpected, f"Unexpected severity values in vw_anomaly_alerts: {unexpected}"

    def test_well_comparison_has_all_wells(self, snowflake_env):
        cur = self._conn.cursor()
        cur.execute(
            "SELECT DISTINCT well_id FROM VOLVE_DB.SERVING.vw_well_comparison "
            "ORDER BY well_id"
        )
        wells = {r[0] for r in cur.fetchall()}
        for well in DATABRICKS_WELLS:
            assert well in wells, f"Well {well} missing from vw_well_comparison"

    def test_kpis_water_cut_in_range(self, snowflake_env):
        row = self._query_one(
            "SELECT COUNT(*) FROM VOLVE_DB.SERVING.vw_daily_production_kpis "
            "WHERE water_cut_pct IS NOT NULL AND (water_cut_pct < 0 OR water_cut_pct > 100)"
        )
        assert row[0] == 0, f"{row[0]} Snowflake KPI rows have water_cut_pct outside [0, 100]"
