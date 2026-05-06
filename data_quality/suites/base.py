"""Shared dataclasses for all DQ suites."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    details: str = ""
    actual_value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class SuiteResult:
    suite_name: str
    table: str
    row_count: int
    run_ts: datetime
    expectations: List[ExpectationResult] = field(default_factory=list)

    @property
    def n_passed(self):
        return sum(1 for e in self.expectations if e.passed)

    @property
    def n_failed(self):
        return sum(1 for e in self.expectations if not e.passed)

    @property
    def n_total(self):
        return len(self.expectations)

    @property
    def pass_rate(self):
        return self.n_passed / self.n_total if self.n_total > 0 else 0.0

    @property
    def success(self):
        return self.pass_rate >= 0.95


def _fetch_scalar(cursor, sql: str) -> any:
    cursor.execute(sql)
    row = cursor.fetchone()
    return row[0] if row else None


def _null_rate(cursor, table: str, column: str) -> tuple[float, int, int]:
    """Returns (null_rate, null_count, total_count)."""
    total = _fetch_scalar(cursor, f"SELECT COUNT(*) FROM {table}")
    if not total:
        return 1.0, 0, 0
    nulls = _fetch_scalar(cursor, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
    return (nulls / total), nulls, total


def expect_row_count_positive(cursor, table: str) -> ExpectationResult:
    count = _fetch_scalar(cursor, f"SELECT COUNT(*) FROM {table}")
    return ExpectationResult(
        name="expect_table_row_count_positive",
        passed=bool(count and count > 0),
        details=f"row_count = {count:,}" if count else "row_count = 0",
        actual_value=count,
        threshold=1,
    )


def expect_not_null_mostly(
    cursor, table: str, column: str, mostly: float = 0.95
) -> ExpectationResult:
    null_rate, nulls, total = _null_rate(cursor, table, column)
    not_null_rate = 1.0 - null_rate
    return ExpectationResult(
        name=f"expect_{column}_not_null_mostly",
        passed=not_null_rate >= mostly,
        details=f"not_null_rate = {not_null_rate:.4f} ({total - nulls}/{total})",
        actual_value=round(not_null_rate, 4),
        threshold=mostly,
    )


def expect_values_in_set(
    cursor, table: str, column: str, value_set: list
) -> ExpectationResult:
    quoted = ", ".join(f"'{v}'" for v in value_set)
    bad = _fetch_scalar(
        cursor,
        f"SELECT COUNT(*) FROM {table} WHERE {column} NOT IN ({quoted}) AND {column} IS NOT NULL",
    )
    return ExpectationResult(
        name=f"expect_{column}_in_set",
        passed=bad == 0,
        details=f"unexpected_values = {bad}  (allowed: {value_set})",
        actual_value=bad,
        threshold=0,
    )


def expect_column_non_negative(
    cursor, table: str, column: str, mostly: float = 0.95
) -> ExpectationResult:
    total = _fetch_scalar(cursor, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL")
    if not total:
        return ExpectationResult(
            name=f"expect_{column}_non_negative",
            passed=True,
            details="all values NULL — skipped",
        )
    bad = _fetch_scalar(
        cursor, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL AND {column} < 0"
    )
    rate = 1.0 - (bad / total)
    return ExpectationResult(
        name=f"expect_{column}_non_negative",
        passed=rate >= mostly,
        details=f"non_negative_rate = {rate:.4f}  (negative_count = {bad}/{total})",
        actual_value=round(rate, 4),
        threshold=mostly,
    )


def expect_column_between(
    cursor, table: str, column: str, min_val: float, max_val: float, mostly: float = 0.95
) -> ExpectationResult:
    total = _fetch_scalar(cursor, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL")
    if not total:
        return ExpectationResult(
            name=f"expect_{column}_between_{min_val}_{max_val}",
            passed=True,
            details="all values NULL — skipped",
        )
    bad = _fetch_scalar(
        cursor,
        f"SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL "
        f"AND ({column} < {min_val} OR {column} > {max_val})",
    )
    rate = 1.0 - (bad / total)
    return ExpectationResult(
        name=f"expect_{column}_between_{min_val}_{max_val}",
        passed=rate >= mostly,
        details=f"in_range_rate = {rate:.4f}  (out_of_range = {bad}/{total})",
        actual_value=round(rate, 4),
        threshold=mostly,
    )
