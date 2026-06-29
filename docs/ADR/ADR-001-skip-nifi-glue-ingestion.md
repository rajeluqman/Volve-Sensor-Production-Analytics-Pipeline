# ADR-001: Skip NiFi + AWS Glue ingestion

**Status:** Accepted | **Date:** original (per `docs/ARCHITECTURE.md` v2.0, "Phase 1 architecture revision")

> Migrated verbatim from `docs/ARCHITECTURE.md` §6 by the 2026-06-29 governance retrofit — real
> rationale already existed there at the time the pivot happened, this is NOT a reconstructed
> ADR. Promoted to its own file so it gets proper ADR numbering/cross-referencing instead of
> being buried in an architecture doc.

## Decision
Databricks Volume direct access replaces the original NiFi → S3 → Glue ingestion path.

## Why
Equinor Volve dataset is available as a Databricks Delta Share
(`equinor_asa_volve_data_village` catalog). Data is already in a Databricks Volume, accessible
via `read_files()` in SQL Warehouse. Building NiFi + Glue would add operational complexity with
no data movement benefit.

## Trade-off
Reduces portfolio breadth (no NiFi demo), but produces a cleaner, more realistic
Databricks-native architecture.

## Consequence (verified 2026-06-29)
`ingestion/nifi/` and `bronze/glue_jobs/` are now orphaned planning stubs — `HOW_IT_WORKS.txt`
files only, referencing scripts (`route_witsml.groovy`, `bronze_production_daily.py`) that were
never built and never will be. `docs/BRD.md`, `docs/DRD.md`, `docs/DQD.md`,
`docs/PIPELINE_SPEC.md` were never updated after this pivot and still describe the pre-ADR-001
design — flagged stale in `CLAUDE.md`, not retroactively rewritten by this retrofit.
