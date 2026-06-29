# ADR-003: TO_JSON() for WITSML nested structs

**Status:** Accepted | **Date:** original (per `docs/ARCHITECTURE.md` v2.0)

> Migrated verbatim from `docs/ARCHITECTURE.md` §6 by the 2026-06-29 governance retrofit —
> real rationale already existed there, not reconstructed.

## Decision
The `trajectoryStation` column is stored as a JSON string in Bronze, not a native struct.

## Why
WITSML XML schema varies between wellbore files (WITSML 1.3.1 vs 1.4.1 have different optional
fields). A `UNION ALL` across multiple trajectory files fails with
`INCOMPATIBLE_COLUMN_TYPE` when struct schemas differ. Serialising to JSON avoids the conflict
at Bronze layer; Silver parses the JSON into flat columns
(`silver/silver_trajectory.py`'s `from_json(trajectory_stations_json, STATION_SCHEMA)` then
explode into one row per survey station).

## Consequence
This is also why the trajectory grain only becomes `(well_id, md_m)` at Silver, not Bronze —
Bronze grain is `(well_id, trajectory_file)` with the stations still nested as JSON.
