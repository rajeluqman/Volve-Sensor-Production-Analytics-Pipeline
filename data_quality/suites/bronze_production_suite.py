"""
Suite: bronze_production_suite
Table: claudecatalog.bronze.raw_production
Target pass rate: > 95%

Expectations (8):
  E1  Table has at least 1 row
  E2  WELL_BORE_CODE not null (>= 95%)
  E3  DATEPRD not null (>= 95%)
  E4  well_id values in {F-1, F-11, F-12}
  E5  BORE_OIL_VOL >= 0 (where not null, >= 95%)
  E6  ingestion_ts not null (100%)
  E7  source_system not null (100%)
  E8  source_file not null (100%)
"""

from datetime import datetime
from .base import (
    SuiteResult,
    expect_row_count_positive,
    expect_not_null_mostly,
    expect_values_in_set,
    expect_column_non_negative,
)

TABLE = "claudecatalog.bronze.raw_production"
SUITE = "bronze_production_suite"


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
        expect_not_null_mostly(cursor, TABLE, "ingestion_ts", mostly=1.0),
        expect_not_null_mostly(cursor, TABLE, "source_system", mostly=1.0),
        expect_not_null_mostly(cursor, TABLE, "source_file", mostly=1.0),
    ]

    return SuiteResult(
        suite_name=SUITE,
        table=TABLE,
        row_count=row_count,
        run_ts=run_ts,
        expectations=expectations,
    )
