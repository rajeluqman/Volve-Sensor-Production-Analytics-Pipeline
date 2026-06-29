# Volve Sensor & Production Analytics Pipeline — AI Context

> Auto-loaded by Claude Code every session. Governance framework ported from
> `creative_intelligence_lab` (CIL) per the pipeline-retrofit effort (repo 4 of 4, last — see
> `architecture/pipeline_retrofit/` in CIL for provenance). Stack is UNCHANGED by the retrofit:
> this file documents the repo as it actually is (verified by reading bronze/, silver/, gold/,
> ml/, snowflake/, airflow/ — NOT the stale docs/BRD.md, DRD.md, DQD.md, PIPELINE_SPEC.md,
> which describe an abandoned NiFi+AWS Glue+Great-Expectations v1.0 design — see "Known doc
> staleness" below).

## 🛑 STOP-GATE — read before ANY model/schema/identity work
This repo is governed. Before you edit a Gold `.py` script, a Silver transform, an ML training
script, or before you "proceed" past a grain/identity question — you MUST:
1. **Open the governing doc first.** Grain/identity → `docs/ADR/ADR-008-identity-grain.md` +
   `docs/DATA_MODEL.md`. Compute boundary (Databricks SQL Warehouse only, no Glue/NiFi/PySpark
   cluster) → `docs/ARCHITECTURE.md` + `tests/boundary_contract.py`. 3-well free-tier cap →
   `docs/ADR/ADR-005-three-well-scope.md` + `INFRA_LIMITS_LOG.md`.
2. **Validate identity BEFORE building downstream.** Every production-data row's grain is
   `(well_id, DATEPRD)` — exactly one row per well per day from Silver onward (dedup via
   `ROW_NUMBER() OVER (PARTITION BY WELL_BORE_CODE, DATEPRD ORDER BY ingestion_ts DESC)` in
   `silver/silver_production.py`). Trajectory grain is `(well_id, md_m)` (one row per survey
   station after exploding `trajectory_stations_json` in `silver/silver_trajectory.py`). Run
   `python tests/identity_contract.py` and `python tests/boundary_contract.py` before calling
   any Silver/Gold change done — these are the binding checks, not your judgement.
3. **If a rule and the request conflict, STOP and surface it** — do not silently proceed.
   Mixed-grain table, Spark/Glue/NiFi compute, a 4th well, a non-Databricks/Snowflake target →
   name it, cite the doc, and ask @data-architect / @scope-guardian before writing code.

Enforced three ways: this prompt (soft), `.claude/hooks/governance_guard.py` (blocks edits to
governed files without a context nudge), and CI (`tests/identity_contract.py` +
`tests/boundary_contract.py` + `tests/doc_reference_contract.py`, blocks the PR).

## 🔁 ANTI-SHORTCUT PROTOCOL — read-before-touch, reconcile-before-done
1. **Read-before-touch** — never edit or assert about a file from memory; read it THIS turn.
   (This repo has the worst pre-existing doc accuracy of the 4 retrofit repos — see below —
   so this rule matters more here than anywhere else in the porting effort.)
2. **Enumerate, don't sample** — for "all N scripts/tables" tasks, get N from `ls`/`grep`
   BEFORE acting (2 Bronze tables, 2 Silver tables, 2 Gold tables, 3 ML models — verify the
   count, don't recall it from README.md, which is occasionally wrong, e.g. table name
   `gold.production_kpis` in `docs/ARCHITECTURE.md` vs the real `gold.production_daily` in
   `gold/gold_production_daily.py`).
3. **Reconcile-before-done** — before saying done/fixed/green, restate the request as a
   numbered checklist with `file:line` evidence per item. No evidence = "unverified".
4. **Tag assumptions** — any unchecked load-bearing claim is marked "(unverified)"; any
   reconstructed ADR rationale (no contemporaneous deliberation found) is marked
   "(reconstructed — owner confirm)".

The machine half: `tests/doc_reference_contract.py` proves every path a Markdown doc
references actually exists. `scripts/gen_repo_map.py` generates `architecture/REPO_MAP.md` —
a pointer index, not a cache; it tells you which file to open, then you read that file fresh.

## ⚠️ Known doc staleness (verified 2026-06-29, ground-truth read — not fixed, flagged)
This repo's `docs/BRD.md`, `docs/DRD.md`, `docs/DQD.md`, `docs/PIPELINE_SPEC.md` are **all
Version 1.0, dated 2026-05-05**, and describe the **original, abandoned** architecture:
NiFi → AWS S3 landing → AWS Glue Bronze → Great Expectations DQ suites, including a 4th data
source (LAS well logs) that isn't in the real pipeline at all. `docs/ARCHITECTURE.md` is
**Version 2.0** and documents the real pivot (ADR-001 in that file: "Skip NiFi + AWS Glue
ingestion" → Databricks Volume + `read_files()` direct access) — it is the only doc-of-record
that matches the code. Do not trust BRD/DRD/DQD/PIPELINE_SPEC for stack, source, or DQ-suite
claims; cross-check against `docs/ARCHITECTURE.md` and the actual script. Concretely:
- `ingestion/nifi/` and `bronze/glue_jobs/` are **orphaned planning stubs** (`HOW_IT_WORKS.txt`
  only, no real code, reference files like `bronze_production_daily.py`/`route_witsml.groovy`
  that don't exist anywhere in the repo) — left in place per owner instruction (flag, don't
  delete) but excluded from the stack table and boundary contract.
- `tests/` and `data_quality/` contain **only a `HOW_IT_WORKS.txt` stub each** — zero real test
  files or Great Expectations suite files exist. README's "Phase 7: Data Quality — Done" and
  the resume claim "84 tests, 0 failures" are **unsupported** — see `INTERVIEW_GUIDE.md`. The
  real DQ gate is inline SQL threshold checks in `airflow/dags/volve_daily_pipeline.py`
  (`DQ_CHECKS_SQL`, task `check_dq_silver`), not Great Expectations.
- `.env.example` still lists AWS S3 / NiFi credentials that nothing in the real pipeline reads.
- Building the missing tests/GE suites is explicitly **deferred** — owner will do this later
  once this governance layer (CLAUDE.md + agents + cikgu) is in place, not in this retrofit pass.

## Project Overview
**Domain**: Oil & gas / sensor production analytics (Equinor Volve open dataset).
**Problem**: Detect production anomalies, predict downhole pressure, and score drilling
efficiency for 3 wells (F-1, F-11, F-12) from the Equinor Volve open dataset, via a
Databricks-native Bronze→Silver→Gold lakehouse, 3 MLflow models, and a Snowflake BI serving
layer.
**Purpose**: Data Engineering portfolio project (single-dev, Raja Ahmad Luqman). Pipeline is
functionally built (Phases 0–8 "Done" per README; Phase 9 testing/doc-finalisation is
genuinely **In Progress**, not done — see staleness section above) — this retrofit adds
governance + learning layers, no pipeline build scope.

## Stack (locked — unchanged by this retrofit, verified by reading the repo)
| Layer | Storage | Compute / engine | Notes |
|-------|---------|------------------|-------|
| Source | Equinor Volve Data Village | Databricks Volume (Delta Share), `equinor_asa_volve_data_village` catalog | public open dataset, not committed to repo |
| Bronze | Databricks Unity Catalog (`claudecatalog.bronze`) | Databricks SQL Warehouse, `read_files()` — REAL logic in `bronze/bronze_production.py`, `bronze/bronze_witsml.py` | raw as-is + `ingestion_ts`/`source_file`/`well_id` metadata |
| Silver | Databricks Unity Catalog (`claudecatalog.silver`) | Databricks SQL Warehouse (SQL CTAS) — REAL logic in `silver/silver_production.py`, `silver/silver_trajectory.py` | type cast, dedup, `water_cut_pct`/`gas_oil_ratio` derived cols, grain `(well_id, DATEPRD)` |
| Gold | Databricks Unity Catalog (`claudecatalog.gold`) | Databricks SQL Warehouse, **no dbt** — REAL logic in `gold/gold_production_daily.py`, `gold/gold_ml_features.py` | KPIs, anomaly flags, ML feature store (lag/rolling features) |
| ML | `claudecatalog.ml.*` registry | MLflow on Databricks — `ml/train_pressure_prediction.py` (XGBoost), `ml/train_drilling_efficiency.py` (Random Forest), `ml/train_anomaly_detection.py` (Isolation Forest), `ml/score_models.py` | 3 models, batch scoring writes `gold.ml_predictions` |
| DQ gate | inline SQL (NOT Great Expectations despite docs/README claims) | `airflow/dags/volve_daily_pipeline.py` `DQ_CHECKS_SQL`, task `check_dq_silver` | blocks Gold tasks if any check fails |
| Orchestration | — | Apache Airflow (Docker, LocalExecutor) — `airflow/dags/volve_daily_pipeline.py`, 10-task DAG | `operators/databricks_sql_operator.py` custom operators |
| Serving | reads Gold via Python connector | Snowflake (`VOLVE_DB.SERVING`), 5 BI views — `snowflake/load_snowflake.py`, `snowflake/create_views.py` | truncate+reload ETL, no dbt |
| Alerting | none today — **Slack backfilled this retrofit** | `airflow/dags/volve_daily_pipeline.py` (`_notify_slack_failure`, `on_failure_callback`) | per 01_OPUS_DECISIONS — Volve is a Slack-backfill repo like olist |

⚠️ Stack boundary (`docs/ARCHITECTURE.md` §3 + `tests/boundary_contract.py`): **all
Bronze/Silver/Gold compute = Databricks SQL Warehouse only** — no PySpark cluster, no AWS Glue,
no NiFi, no AWS S3 as live storage (the `.env.example` AWS/NiFi vars are dead config — see
staleness section). **ML training/scoring = local Python + MLflow tracking to Databricks**, no
Spark MLlib. **Serving = Snowflake only**, loaded via direct Python connector — no dbt anywhere
in this repo (unlike home-credit/olist/paysim). 3 wells only (F-1, F-11, F-12) — free-tier SQL
Warehouse constraint, see `docs/ADR/ADR-005-three-well-scope.md` + `INFRA_LIMITS_LOG.md`.

## Architecture of Record
`docs/ARCHITECTURE.md` (v2.0, the doc-of-record — contains 7 inline ADRs migrated to
`docs/ADR/` by this retrofit, see below), `docs/OPS_RUNBOOK.md` (also stale — references NiFi/
Glue playbooks, flagged not fixed). **Stale, do not trust for stack claims**: `docs/BRD.md`,
`docs/DRD.md`, `docs/DQD.md`, `docs/PIPELINE_SPEC.md` (all v1.0). `architecture/REPO_MAP.md`
(generated, see Anti-Shortcut Protocol above).

**Identity key**: `(well_id, DATEPRD)` for production grain, `(well_id, md_m)` for trajectory
grain (no SCD — Gold tables are full rebuilds via `CREATE TABLE ... AS` on each run, not
incremental MERGE; see `docs/ADR/ADR-008-identity-grain.md`).

**Governance gate**: @data-architect holds veto on grain/Gold-script changes; @scope-guardian
holds veto on stack/scope creep (no compute outside Databricks SQL Warehouse + Snowflake
serving, no 4th well, no dbt introduction, no reviving the NiFi/Glue stub directories).

## Governed-file map
| Path | Governed by | Cite before editing |
|---|---|---|
| `gold/gold_production_daily.py`, `gold/gold_ml_features.py` | @data-architect | `docs/ADR/ADR-008-identity-grain.md`, `docs/DATA_MODEL.md` |
| `silver/silver_production.py`, `silver/silver_trajectory.py` | @data-architect | grain dedup logic, `docs/DATA_MODEL.md` |
| `ml/train_*.py` | @data-architect | `docs/ADR/ADR-009-ml-model-selection.md` |
| `docs/DATA_MODEL.md` | @data-architect | grain doctrine |
| `docs/ADR/` | @data-architect + @documentation-sherpa | ADR numbering, cross-references |
| `airflow/dags/volve_daily_pipeline.py` | @scope-guardian + @data-platform-engineer | `docs/ARCHITECTURE.md`, 3-well scope |
| `snowflake/*.py` | @scope-guardian | `docs/ARCHITECTURE.md` — Snowflake is serving-only, never a transform engine |
| `.env.example` | @scope-guardian | flag dead AWS/NiFi vars; do not add real new ones without an ADR |

## Known resume↔repo mismatch (flagged, not silently fixed)
The resume claim "84 tests, 0 failures" does **not** match this repo: `tests/` contains only a
`HOW_IT_WORKS.txt` stub, zero `.py` test files exist anywhere (`find tests -type f` → 1 file).
See `INTERVIEW_GUIDE.md` "Resume Claim ↔ Repo Evidence" — recommend either building real tests
before claiming this number, or removing the claim until then.

## Cabinet (11 agents) — see `.claude/agents/`
**Veto holders**: @data-architect (Opus, grain/model) · @scope-guardian (Sonnet, stack/scope).
**Build**: @senior-data-engineer (Bronze/Silver/Gold scripts + Airflow, absorbs QA) ·
@data-quality-steward (the inline SQL DQ gate + DQD.md staleness ownership) · @product-owner
(BRD/KPIs) · @business-analyst (DRD + resume-claim reconciliation) · @data-platform-engineer
(Airflow/Databricks/Snowflake infra, Slack backfill, absorbs devops) · @documentation-sherpa
(docs/ADR/REPO_MAP/Confluence upkeep — heaviest load of the 4 repos given the doc staleness) ·
@finops-agent (Databricks $400 trial credit + Snowflake 30-day trial burn) ·
@infra-reality-agent (3/29-well free-tier ceiling, `INFRA_LIMITS_LOG.md`).
**Teaching**: @cikgu (English-first, mental-model → ETL use-case → production bug → debug →
syntax LAST) — NOT a build agent; runs `learning/CURRICULUM.md` drills on `drill/*` branches,
never `main`.

Largest roster of the 4 retrofit repos (10 build/veto + cikgu = 11) — matches `01_OPUS_DECISIONS.md`
("Volve 11"): both `finops-agent` and `infra-reality-agent` seats are populated here (trial-credit
burn risk + free-tier well-count ceiling are both real, documented risks unique to this repo).

## What NOT to commit
`.env*`, `data/`, `*.parquet`, raw Volve dataset files (Equinor's open-data licence — not
ours to redistribute), `COST_LOG.md` if it ever contains real account IDs.

## Token Discipline
1. Checkpoint first: read `PROJECT_STATUS.md` "▶ RESUME HERE" before reading code.
2. Use `architecture/REPO_MAP.md` instead of re-grepping the whole repo for "where is X".
3. Read only files in the current module — max ~3 files/turn.
4. Trust `docs/ARCHITECTURE.md` (v2.0) over BRD/DRD/DQD/PIPELINE_SPEC (stale v1.0) for any
   stack/source/DQ claim — and say so explicitly if a doc conflict comes up mid-task.
