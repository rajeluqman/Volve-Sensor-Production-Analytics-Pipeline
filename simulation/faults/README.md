# Fault Catalog — Volve Simulation Lab

Named, reversible faults for troubleshooting drills. `inject.py <fault_id>` applies one;
`reset.py` rebuilds clean sim state from sim fixtures (never hand-patched). No dbt project to
reset here — ADR-008 — sim fixtures are synthetic Excel/WITSML inputs run through the real
scripts pointed at `sim_`-prefixed Unity Catalog tables.

| ID | Fault | Mirrors a real risk from |
|---|---|---|
| F01 | Silver production dedup loses `ORDER BY ingestion_ts DESC` in the `ROW_NUMBER()` window — duplicate `(well_id, DATEPRD)` rows reappear | `silver/silver_production.py`, `tests/identity_contract.py` ID1 |
| F02 | WITSML `trajectory_stations_json` explode step skipped — trajectory grain collapses back to 1 row per file instead of 1 per survey station | `silver/silver_trajectory.py`, `tests/identity_contract.py` ID3 |
| F03 | Snowflake load truncate step skipped (`snowflake/load_snowflake.py`) — stale rows persist alongside the new load, doubling BI view counts | `snowflake/load_snowflake.py`, `snowflake/create_views.py` |
| F04 | 3-well scope filter dropped (`well_id IN ('F-1','F-11','F-12')`) — a 4th well's rows leak into Silver/Gold | `silver/silver_production.py`, `docs/ADR/ADR-005-three-well-scope.md`, `tests/boundary_contract.py` ST5 |

Catalog entries (full repro steps) live in `simulation/faults/catalog/`.
