"""
Unit tests for SQL string structure in Bronze, Silver, and Gold scripts.

Imports the SQL constants directly from each layer script and asserts that
the expected clauses, tables, columns, and partitioning logic are present.
No database connection required.
"""

import sys
import os
import pytest

# Add repo root to path so imports from bronze/ silver/ gold/ work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Bronze — Production
# ---------------------------------------------------------------------------

class TestBronzeProductionSQL:
    """SQL structure checks for bronze/bronze_production.py."""

    @pytest.fixture(autouse=True)
    def _import(self):
        # Monkey-patch env vars so the module-level os.environ[] calls succeed
        env_patch = {
            "DATABRICKS_HOST": "https://fake.databricks.com",
            "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/fake",
            "DATABRICKS_TOKEN": "fake-token",
        }
        original = {k: os.environ.get(k) for k in env_patch}
        os.environ.update(env_patch)
        import bronze.bronze_production as mod
        self.mod = mod
        yield
        # Restore
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_target_table(self):
        assert "claudecatalog.bronze.raw_production" in self.mod.SQL_CREATE_TABLE

    def test_partitioned_by(self):
        assert "PARTITIONED BY" in self.mod.SQL_CREATE_TABLE
        assert "date_year" in self.mod.SQL_CREATE_TABLE
        assert "well_id" in self.mod.SQL_CREATE_TABLE

    def test_well_id_derived_column(self):
        assert "REGEXP_EXTRACT" in self.mod.SQL_CREATE_TABLE
        assert "well_id" in self.mod.SQL_CREATE_TABLE

    def test_ingestion_timestamp_column(self):
        assert "ingestion_ts" in self.mod.SQL_CREATE_TABLE

    def test_source_system_column(self):
        assert "source_system" in self.mod.SQL_CREATE_TABLE

    def test_header_row_filtered(self):
        # Bronze skips the literal 'DATEPRD' header row
        assert "DATEPRD" in self.mod.SQL_CREATE_TABLE
        assert "!=" in self.mod.SQL_CREATE_TABLE or "!= 'DATEPRD'" in self.mod.SQL_CREATE_TABLE

    def test_wells_in_scope(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "F-1" in sql
        assert "F-11" in sql
        assert "F-12" in sql

    def test_production_volume_columns(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "BORE_OIL_VOL" in sql
        assert "BORE_GAS_VOL" in sql
        assert "BORE_WAT_VOL" in sql

    def test_drop_table_is_if_exists(self):
        assert "IF EXISTS" in self.mod.SQL_DROP_TABLE

    def test_create_schema_if_not_exists(self):
        assert "IF NOT EXISTS" in self.mod.SQL_CREATE_SCHEMA


# ---------------------------------------------------------------------------
# Silver — Production
# ---------------------------------------------------------------------------

class TestSilverProductionSQL:
    """SQL structure checks for silver/silver_production.py."""

    @pytest.fixture(autouse=True)
    def _import(self):
        env_patch = {
            "DATABRICKS_HOST": "https://fake.databricks.com",
            "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/fake",
            "DATABRICKS_TOKEN": "fake-token",
        }
        original = {k: os.environ.get(k) for k in env_patch}
        os.environ.update(env_patch)
        import silver.silver_production as mod
        self.mod = mod
        yield
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_target_table(self):
        assert "claudecatalog.silver.cleaned_production" in self.mod.SQL_CREATE_TABLE

    def test_source_table(self):
        assert "claudecatalog.bronze.raw_production" in self.mod.SQL_CREATE_TABLE

    def test_dedup_row_number(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "ROW_NUMBER" in sql
        assert "ingestion_ts DESC" in sql

    def test_type_cast_numeric_columns(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "TRY_CAST" in sql
        assert "DOUBLE" in sql

    def test_derived_water_cut(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "water_cut_pct" in sql
        assert "BORE_WAT_VOL" in sql

    def test_derived_gor(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "gas_oil_ratio" in sql
        assert "BORE_GAS_VOL" in sql
        assert "BORE_OIL_VOL" in sql

    def test_quality_flag_zero_prod(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "is_zero_prod_uptime" in sql

    def test_quality_flag_pressure_valid(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "is_pressure_valid" in sql

    def test_pressure_range_bounds(self):
        # 0–10000 psi per CLAUDE.md
        sql = self.mod.SQL_CREATE_TABLE
        assert "10000" in sql

    def test_partitioned_by(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "PARTITIONED BY" in sql
        assert "date_year" in sql
        assert "well_id" in sql

    def test_null_filtering(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "IS NOT NULL" in sql


# ---------------------------------------------------------------------------
# Gold — Production Daily
# ---------------------------------------------------------------------------

class TestGoldProductionSQL:
    """SQL structure checks for gold/gold_production_daily.py."""

    @pytest.fixture(autouse=True)
    def _import(self):
        env_patch = {
            "DATABRICKS_HOST": "https://fake.databricks.com",
            "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/fake",
            "DATABRICKS_TOKEN": "fake-token",
        }
        original = {k: os.environ.get(k) for k in env_patch}
        os.environ.update(env_patch)
        import gold.gold_production_daily as mod
        self.mod = mod
        yield
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_target_table(self):
        assert "claudecatalog.gold.production_daily" in self.mod.SQL_CREATE_TABLE

    def test_source_table(self):
        assert "claudecatalog.silver.cleaned_production" in self.mod.SQL_CREATE_TABLE

    def test_pressure_delta(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "pressure_delta_24h" in sql

    def test_anomaly_flags_present(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "is_anomaly_pressure" in sql
        assert "is_water_cut_spike" in sql
        assert "is_gor_anomaly" in sql

    def test_rolling_averages(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "7d_avg" in sql or "7D_AVG" in sql.upper() or "ROWS BETWEEN 6 PRECEDING" in sql

    def test_lag_function_used(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "LAG(" in sql

    def test_baseline_gor(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "baseline_gor" in sql

    def test_anomaly_pressure_threshold(self):
        # 500 psi threshold from CLAUDE.md
        sql = self.mod.SQL_CREATE_TABLE
        assert "500" in sql

    def test_partitioned_by(self):
        sql = self.mod.SQL_CREATE_TABLE
        assert "PARTITIONED BY" in sql
        assert "date_year" in sql
        assert "well_id" in sql
