"""
Suite: silver_witsml_suite
Table: claudecatalog.silver.cleaned_trajectory
Target pass rate: > 95%

Expectations (8):
  E1  Table has at least 1 row
  E2  well_id not null (>= 95%)
  E3  well_id values in {F-1, F-11, F-12}
  E4  md_m >= 0 (where not null, >= 95%)
  E5  incl_deg between 0 and 180 (where not null, >= 95%)
  E6  azi_deg between 0 and 360 (where not null, >= 95%)
  E7  tvd_m >= 0 (where not null, >= 95%)
  E8  is_md_valid not null (>= 95%)
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

TABLE = "claudecatalog.silver.cleaned_trajectory"
SUITE = "silver_witsml_suite"


def run(cursor) -> SuiteResult:
    run_ts = datetime.utcnow()

    cursor.execute(f"SELECT COUNT(*) FROM {TABLE}")
    row_count = cursor.fetchone()[0] or 0

    expectations = [
        expect_row_count_positive(cursor, TABLE),
        expect_not_null_mostly(cursor, TABLE, "well_id", mostly=0.95),
        expect_values_in_set(cursor, TABLE, "well_id", ["F-1", "F-11", "F-12"]),
        expect_column_non_negative(cursor, TABLE, "md_m", mostly=0.95),
        expect_column_between(cursor, TABLE, "incl_deg", 0, 180, mostly=0.95),
        expect_column_between(cursor, TABLE, "azi_deg", 0, 360, mostly=0.95),
        expect_column_non_negative(cursor, TABLE, "tvd_m", mostly=0.95),
        expect_not_null_mostly(cursor, TABLE, "is_md_valid", mostly=0.95),
    ]

    return SuiteResult(
        suite_name=SUITE,
        table=TABLE,
        row_count=row_count,
        run_ts=run_ts,
        expectations=expectations,
    )
