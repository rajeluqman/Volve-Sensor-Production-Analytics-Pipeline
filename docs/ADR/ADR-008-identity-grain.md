# ADR-008: Identity grain — (well_id, DATEPRD) production, (well_id, md_m) trajectory, no dbt/no SCD

**Status:** Accepted | **Date:** 2026-06-29 (written by this retrofit)

> NEW ADR, not migrated — `docs/ARCHITECTURE.md` documents the grain implicitly (§4 "Data
> Flow") but never states it as a decision record. Written from direct code reading
> (`silver/silver_production.py`, `silver/silver_trajectory.py`, `gold/gold_production_daily.py`),
> not reconstructed from a doc — the rationale is observable in the code itself.

## Decision
1. **Production grain**: `(well_id, DATEPRD)` — exactly one row per well per day, from Silver
   onward. Enforced by `silver/silver_production.py`'s
   `ROW_NUMBER() OVER (PARTITION BY WELL_BORE_CODE, DATEPRD ORDER BY ingestion_ts DESC)` dedup
   window, keeping latest `ingestion_ts` per key.
2. **Trajectory grain**: `(well_id, md_m)` — one row per survey station, after
   `silver/silver_trajectory.py` explodes `trajectory_stations_json` (ADR-003) into flat
   columns.
3. **No dbt, no SCD2**: unlike home-credit/olist/paysim (all of which use dbt + at least one
   SCD2 dimension), this repo's Gold layer is hand-written Databricks SQL
   (`gold/gold_production_daily.py`, `gold/gold_ml_features.py`), and every Gold table is a
   full `CREATE TABLE ... AS` rebuild on each pipeline run — there is no incremental MERGE, no
   historical versioning beyond Delta's native time-travel.

## Why
- The production/trajectory split reflects the two genuinely different source shapes (daily
  Excel rows vs. nested WITSML survey stations) — forcing them into one grain would either
  lose station-level fidelity or duplicate daily production rows per station, both wrong.
- No SCD2 is appropriate here: there is no "current vs. historical" dimension concept in this
  domain (a well's `well_id` doesn't change over time the way a customer's address does) — the
  closest analogue, well metadata, isn't even modeled as a dimension table in this repo.
  Adding SCD2 would be importing a pattern from the other 3 repos without a domain reason.
- Full-rebuild Gold is acceptable at this data volume (4,967 production rows, 22 trajectories)
  — at this scale, incremental MERGE complexity isn't worth it; this would need revisiting if
  the 3-well scope (ADR-005) were ever expanded.

## Enforcement
`tests/identity_contract.py` checks the dedup window, well filter, and station-explode logic
statically (no live Databricks connection required).
