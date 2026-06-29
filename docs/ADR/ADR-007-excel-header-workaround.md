# ADR-007: Excel header row workaround

**Status:** Accepted | **Date:** original (per `docs/ARCHITECTURE.md` v2.0)

> Migrated verbatim from `docs/ARCHITECTURE.md` §6 by the 2026-06-29 governance retrofit —
> real rationale already existed there, not reconstructed.

## Decision
Hardcode column aliases (`_c0` → `DATEPRD`, `_c1` → `WELL_BORE_CODE`, etc.) in
`bronze/bronze_production.py` and filter the header row with `WHERE _c0 != 'DATEPRD'`.

## Why
Databricks SQL Warehouse `read_files(format='excel')` does not automatically detect the
header row — all columns are returned as `_c0`, `_c1`, etc. The first data row contains the
actual column names. This workaround correctly handles the 24-column production Excel file.
