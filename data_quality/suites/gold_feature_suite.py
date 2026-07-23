"""
Suite: gold_feature_suite
Table: claudecatalog.gold.ml_feature_store
Target pass rate: > 95%

Expectations (9):
  E1  Table has at least 1 row
  E2  well_id not null (>= 95%)
  E3  DATEPRD not null (>= 95%)
  E4  BORE_OIL_VOL >= 0 (where not null, >= 95%)
  E5  pressure_lag1 not null (>= 70%  — lag window produces leading NULLs)
  E6  water_cut_lag1 not null (>= 70%)
  E7  gor_lag1 not null (>= 70%)
  E8  next_day_pressure not null (>= 70%  — LEAD produces trailing NULL on last date)
  E9  is_anomaly not null (>= 90%)
"""

from datetime import datetime
from .base import (
    SuiteResult,
    expect_row_count_positive,
    expect_not_null_mostly,
    expect_column_non_negative,
)

TABLE = "claudecatalog.gold.ml_feature_store"
SUITE = "gold_feature_suite"


def run(cursor) -> SuiteResult:
    run_ts = datetime.utcnow()

    cursor.execute(f"SELECT COUNT(*) FROM {TABLE}")
    row_count = cursor.fetchone()[0] or 0

    expectations = [
        expect_row_count_positive(cursor, TABLE),
        expect_not_null_mostly(cursor, TABLE, "well_id", mostly=0.95),
        expect_not_null_mostly(cursor, TABLE, "DATEPRD", mostly=0.95),
        expect_column_non_negative(cursor, TABLE, "BORE_OIL_VOL", mostly=0.95),
        # Lag/lead features have natural NULLs at window boundaries — threshold relaxed to 70%
        expect_not_null_mostly(cursor, TABLE, "pressure_lag1", mostly=0.70),
        expect_not_null_mostly(cursor, TABLE, "water_cut_lag1", mostly=0.70),
        expect_not_null_mostly(cursor, TABLE, "gor_lag1", mostly=0.70),
        expect_not_null_mostly(cursor, TABLE, "next_day_pressure", mostly=0.70),
        expect_not_null_mostly(cursor, TABLE, "is_anomaly", mostly=0.90),
    ]

    return SuiteResult(
        suite_name=SUITE,
        table=TABLE,
        row_count=row_count,
        run_ts=run_ts,
        expectations=expectations,
    )
