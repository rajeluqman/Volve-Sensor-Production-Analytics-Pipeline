# SIM-03: Optimization drill — Snowflake truncate+reload vs incremental

**Type:** Optimization drill | **Fault:** F03 | **Branch:** `drill/sim-03-snowflake-optimize`

## Scenario
The real `snowflake/load_snowflake.py` does a full truncate+reload on every run (4,967 rows,
cheap at this volume). Practice reasoning about WHEN that stops being the right call.

## Goal
Inject F03 (truncate step skipped) to see the duplicate-row symptom, fix it, THEN — without
breaking the real repo's truncate+reload pattern — write up (in the sim spec, not real code)
at what row-count threshold an incremental MERGE would become worth the added complexity, and
why this repo's data volume doesn't cross that threshold (ADR-005 free-tier 3-well scope is
part of the answer).

## Acceptance criteria
- F03 fixed in the sim copy
- Written threshold-reasoning paragraph, cross-checked against ADR-005
- `python simulation/check_isolation.py` passes
