# INFRA_LIMITS_LOG.md — Volve Sensor & Production Analytics Pipeline

> Owned by @infra-reality-agent. Real, observed or projected resource ceilings — not guesses.

| Ceiling | Limit | Source | Status |
|---------|-------|--------|--------|
| Wells in scope | 3 of 29 (F-1, F-11, F-12) | `docs/ADR/ADR-005-three-well-scope.md` — free-tier SQL Warehouse credit constraint, full 29-well estimated at ~10× DBU cost | locked, enforced by `silver/silver_production.py` filter + `tests/boundary_contract.py` ST5 |
| GitHub Codespaces RAM | 8GB total, 2 cores | `docs/ARCHITECTURE.md` §5 | Airflow Docker (~3.5GB) and NiFi Docker (~4GB, moot — NiFi never built, ADR-001) must not run concurrently |
| Databricks SQL Warehouse | Serverless Starter (Small), 10-min auto-stop | `docs/ARCHITECTURE.md` §3 | confirm auto-stop is never disabled — main lever against $400 trial-credit burn |
| Snowflake | X-Small warehouse, 30-day trial | `docs/ARCHITECTURE.md` §5 | trial expiry date not yet tracked — add once a real load is run |
| Production data volume | 4,967 rows (3 wells, 2007–2016) | README.md | well within free-tier; informs the "no incremental MERGE needed" call in ADR-008 |
| WITSML trajectory volume | 22 trajectories | `docs/ARCHITECTURE.md` §4 | sampled, not the full 11,664-file WITSML set |

## Note on the abandoned NiFi/Glue infra plan
`docs/ARCHITECTURE.md` §5's "NiFi Docker (if used)" RAM line and the AWS S3 cost estimate are
both holdovers from the pre-ADR-001 design — moot for the real pipeline, kept here only because
the underlying RAM-ceiling lesson (don't run 2 heavy Docker services concurrently on 8GB) still
generalizes to any future infra proposal.
