# ADR-005: 3 wells only (F-1, F-11, F-12)

**Status:** Accepted | **Date:** original (per `docs/ARCHITECTURE.md` v2.0)

> Migrated verbatim from `docs/ARCHITECTURE.md` §6 by the 2026-06-29 governance retrofit —
> real rationale already existed there, not reconstructed. Also the basis for
> `INFRA_LIMITS_LOG.md` (@infra-reality-agent) and `tests/boundary_contract.py` ST5.

## Decision
Process only F-1, F-11, F-12 from the 29 available Volve wells.

## Why
Free-tier SQL Warehouse credit constraint. Full 29-well processing was estimated at 10× the
DBU cost. 3 wells provide sufficient variety (different operators, different production
periods) for meaningful analytics and ML.

## Enforcement
`silver/silver_production.py`'s `well_id IN ('F-1', 'F-11', 'F-12')` filter is the actual
enforcement point — checked by `tests/boundary_contract.py` ST5 and `tests/identity_contract.py`
ID2. Any proposal to add a 4th well requires amending this ADR first, per @scope-guardian.
