# SIM-04: Value-reconciliation drill — 3-well scope leak

**Type:** Value-reconciliation drill | **Fault:** F04 | **Branch:** `drill/sim-04-well-scope`

## Scenario
Inject F04 (well filter dropped) against sim fixtures that include a synthetic 4th well's
rows. Reconcile the resulting row counts/KPI totals against the expected 3-well baseline.

## Goal
Quantify the value impact (e.g. "+X% oil volume from a well that shouldn't be in scope") the
way a real data-quality incident review would, then fix the filter and reconcile again to
zero discrepancy.

## Acceptance criteria
- Before/after row-count and KPI-total reconciliation table written
- Filter restored, `tests/boundary_contract.py` ST5 logic re-verified against the sim copy
- `python simulation/check_isolation.py` passes
