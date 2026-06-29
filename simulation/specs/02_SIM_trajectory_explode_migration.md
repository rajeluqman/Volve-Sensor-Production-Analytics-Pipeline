# SIM-02: Migration drill — trajectory explode logic

**Type:** Migration drill | **Fault:** F02 | **Branch:** `drill/sim-02-trajectory-explode`

## Scenario
Practice migrating the WITSML trajectory explode step (`silver_trajectory.py`) to a
hypothetical new schema version (e.g. WITSML 1.4.1 adds a new optional station field) without
breaking the `(well_id, md_m)` grain.

## Goal
Add a new optional field to the sim `STATION_SCHEMA`, regenerate the explode logic, verify the
grain (one row per survey station, not per file) holds via `tests/identity_contract.py` ID3
logic applied to the sim copy.

## Acceptance criteria
- New field added without changing existing column names/types
- Grain verified unchanged (still 1 row per station)
- `python simulation/check_isolation.py` passes
