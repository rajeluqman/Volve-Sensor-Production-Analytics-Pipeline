# Isolation Contract — Volve Simulation Lab

> `simulation/` is the practice lab for drills (migration, troubleshoot, optimization,
> value-reconciliation) on `drill/*`/`gym/*` branches. Faults only mutate sim state, never the
> real pipeline. Enforced by `simulation/check_isolation.py`, run before every sim session and
> in CI.

## Rules
- **R1 — own storage namespace.** No sim SQL/script may reference the real Unity Catalog
  namespace `claudecatalog.{bronze,silver,gold,ml}`. Any sim Delta table reference must use a
  `sim_` prefixed catalog (e.g. `sim_catalog.bronze.raw_production`).
- **R2 — own Snowflake database.** No sim script may reference `VOLVE_DB`. Use a separate sim
  database name if a drill needs Snowflake serving-layer practice.
- **R3 — no dbt project to isolate.** Unlike home-credit/olist/paysim, this repo has no dbt
  project (ADR-008) — there is no "sim dbt project name must differ from real" rule here.
- **R4 (human-checked) — drills run on `drill/*`/`gym/*` branches, never `main`.**
- **R5 (human-checked) — faults are reversible.** `simulation/faults/inject.py` /
  `reset.py` only mutate files under `simulation/`, never `bronze/`, `silver/`, `gold/`, `ml/`,
  `snowflake/`, or `airflow/dags/` outside the sim tree.

## Run
```
python simulation/check_isolation.py
```
