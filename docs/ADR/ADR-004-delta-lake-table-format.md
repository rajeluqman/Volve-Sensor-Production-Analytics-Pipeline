# ADR-004: Delta Lake as table format

**Status:** Accepted | **Date:** original (per `docs/ARCHITECTURE.md` v2.0)

> Migrated verbatim from `docs/ARCHITECTURE.md` §6 by the 2026-06-29 governance retrofit —
> real rationale already existed there, not reconstructed.

## Decision
All layers (Bronze/Silver/Gold) use Delta tables, Unity Catalog managed
(`claudecatalog.bronze.*`, `claudecatalog.silver.*`, `claudecatalog.gold.*`).

## Why
ACID transactions, time travel (data rollback), schema evolution, MERGE operations. Delta is
the Databricks-native format and deeply integrated with Unity Catalog governance.

## Consequence
Note this repo does NOT use Delta's MERGE for incremental upserts in Gold — Gold tables are
full `CREATE TABLE ... AS` rebuilds each run (see ADR-008). MERGE capability is used implicitly
in Silver's dedup logic only insofar as the table is fully recreated, not merged row-by-row.
