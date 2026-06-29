# SIM-01: Troubleshoot — Silver production dedup grain break

**Type:** Troubleshoot drill | **Fault:** F01 | **Branch:** `drill/sim-01-silver-dedup`

## Scenario
Inject F01 (`simulation/faults/inject.py F01`) — the `ROW_NUMBER()` dedup window in a `sim_`
copy of `silver_production.py` loses `ORDER BY ingestion_ts DESC`. Duplicate `(well_id,
DATEPRD)` rows now exist in the sim Silver table.

## Goal
Diagnose the break using only the symptom (duplicate rows in a query result), not by reading
the injected diff first. Identify the missing `ORDER BY` clause, fix it, verify
`tests/identity_contract.py` ID1 passes against the fixed sim copy's logic.

## Acceptance criteria
- Root cause stated in your own words before looking at the real `silver_production.py`
- Fix applied to the `sim_` copy only
- `python simulation/check_isolation.py` still passes after the fix
- `python simulation/faults/reset.py` run at drill end
