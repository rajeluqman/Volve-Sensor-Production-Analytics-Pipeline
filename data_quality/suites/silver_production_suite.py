"""
Suite: silver_production_suite
Table: claudecatalog.silver.cleaned_production
Target pass rate: > 95%

Expectations (10):
  E1  Table has at least 1 row
  E2  WELL_BORE_CODE not null (>= 95%)
  E3  DATEPRD not null (>= 95%)
  E4  well_id values in {F-1, F-11, F-12}
  E5  BORE_OIL_VOL >= 0 (where not null, >= 95%)
  E6  water_cut_pct between 0 and 100 (where not null, >= 95%)
  E7  AVG_DOWNHOLE_PRESSURE between 0 and 10000 (where not null, >= 95%)
  E8  gas_oil_ratio >= 0 (where not null, >= 95%)
  E9  is_pressure_valid not null (>= 95%)
  E10 is_zero_prod_uptime not null (>= 95%)
"""

from datetime import datetime
from .base import (
    SuiteResult,
    expect_row_count_positive,
    expect_not_null_mostly,
    expect_values_in_set,
    expect_column_non_negative,
    expect_column_between,
)

TABLE = "claudecatalog.silver.cleaned_production"
SUITE = "silver_production_suite"


def run(cursor) -> SuiteResult:
    run_ts = datetime.utcnow()

    cursor.execute(f"SELECT COUNT(*) FROM {TABLE}")
    row_count = cursor.fetchone()[0] or 0

    expectations = [
        expect_row_count_positive(cursor, TABLE),
        expect_not_null_mostly(cursor, TABLE, "WELL_BORE_CODE", mostly=0.95),
        expect_not_null_mostly(cursor, TABLE, "DATEPRD", mostly=0.95),
        expect_values_in_set(cursor, TABLE, "well_id", ["F-1", "F-11", "F-12"]),
        expect_column_non_negative(cursor, TABLE, "BORE_OIL_VOL", mostly=0.95),
        expect_column_between(cursor, TABLE, "water_cut_pct", 0, 100, mostly=0.95),
        expect_column_between(cursor, TABLE, "AVG_DOWNHOLE_PRESSURE", 0, 10000, mostly=0.95),
        expect_column_non_negative(cursor, TABLE, "gas_oil_ratio", mostly=0.95),
        expect_not_null_mostly(cursor, TABLE, "is_pressure_valid", mostly=0.95),
        expect_not_null_mostly(cursor, TABLE, "is_zero_prod_uptime", mostly=0.95),
    ]

    return SuiteResult(
        suite_name=SUITE,
        table=TABLE,
        row_count=row_count,
        run_ts=run_ts,
        expectations=expectations,
    )
