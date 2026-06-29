# PROJECT_STATUS.md — Volve Sensor & Production Analytics Pipeline

## ▶ RESUME HERE
**Where we are:** Governance + learning retrofit complete on branch
`framework/governance-retrofit` (pipeline-retrofit effort, repo 4 of 4 — see
`creative_intelligence_lab/architecture/pipeline_retrofit/PROJECT_STATUS.md` for the
cross-repo tracker). All 11 agents, hook, 3 contracts, ADRs, DATA_MODEL/DATA_DICTIONARY,
Slack backfill, Confluence sync, learning/CURRICULUM.md, simulation/ lab, INTERVIEW_GUIDE.md,
and CI are built and verified green.

**Biggest real finding this build:** this repo had the worst pre-existing doc accuracy of the
4 retrofit repos — `docs/BRD.md`/`DRD.md`/`DQD.md`/`PIPELINE_SPEC.md` are all stale v1.0,
describing an abandoned NiFi+AWS Glue+Great Expectations design; `ingestion/nifi/` and
`bronze/glue_jobs/` are orphaned `HOW_IT_WORKS.txt`-only stubs; `tests/` and `data_quality/`
contain zero real code despite README claiming Phase 7 "Done" and a resume bullet claiming
"84 tests, 0 failures". Per owner instruction (2026-06-29): **flagged everywhere, not
deleted**, and building the missing tests/GE suites is explicitly **deferred** to a future
session once this governance layer is in place.

**Push deferred** (same as the other 3 repos, owner decision 2026-06-28/29): do not push, do
not touch `main`. Opus settles all 4 repos' pushes/PRs in one pass.

**Next step when resuming:** nothing left to build in THIS repo's retrofit. The cross-repo
next step is Opus handling push/PR for all 4 repos — see CIL's
`architecture/pipeline_retrofit/PROJECT_STATUS.md`.

## Build checklist (evidence = file:line, not "done")
- ✅ `CLAUDE.md` — real stack (Databricks SQL Warehouse only, no dbt), stop-gate, anti-shortcut,
  staleness flags, governed-file map
- ✅ `.claude/agents/` ×11 (data-architect, scope-guardian, senior-data-engineer,
  data-quality-steward, product-owner, business-analyst, data-platform-engineer,
  documentation-sherpa, finops-agent, infra-reality-agent, cikgu)
- ✅ `.claude/hooks/governance_guard.py` + `.claude/settings.json`
- ✅ `tests/identity_contract.py`, `boundary_contract.py`, `doc_reference_contract.py` — all
  pass (`python tests/*.py` exit 0)
- ✅ `scripts/gen_repo_map.py` run for real → `architecture/REPO_MAP.md` (64+ files mapped),
  `--check` passes
- ✅ `docs/ADR/ADR-001` through `ADR-007` — migrated verbatim from `docs/ARCHITECTURE.md` §6
  (real rationale, not reconstructed); `ADR-008` (identity grain) new; `ADR-009` (ML model
  selection) new, tagged "(reconstructed — owner confirm)"
- ✅ `docs/DATA_MODEL.md` + `docs/DATA_DICTIONARY.md` — new, previously missing entirely
- ✅ Slack: backfilled `_notify_slack_failure` in `airflow/dags/volve_daily_pipeline.py`
  (`on_failure_callback`), ported from CIL's pattern
- ✅ Confluence: `scripts/sync_docs_to_confluence.py` + `confluence/00_START_HERE.md`
- ✅ Logs: this file, `COST_LOG.md`, `DECISION_LOG.md`, `INFRA_LIMITS_LOG.md` (Volve gets the
  infra log per `01_OPUS_DECISIONS.md`)
- ✅ `INTERVIEW_GUIDE.md` — Resume↔Evidence table, "84 tests"/"Phase 7 Done" both flagged
  unsupported
- ✅ `learning/CURRICULUM.md` (12 modules, M0/M8/M11 unique to this repo's doc-honesty gap) +
  `learning/LEARNING_LOG.md`; `simulation/` (ISOLATION_CONTRACT.md, check_isolation.py,
  faults/, 4 drill specs) — isolation contract passes
- ✅ `.github/workflows/ci.yml` — created fresh (Volve had none), wires the 3 contracts +
  repo-map --check + isolation check
- ✅ README.md "Build Status" — Phase 7 corrected (Data Quality is real but inline-SQL, not
  Great Expectations); Phase 9 kept "In Progress" (was already accurate, verified not to
  silently round up to "Done")
- ⬜ **push feature branch + PR — NOT DONE** (owner cannot push from this environment, KIV'd —
  same as home-credit/olist/paysim; Opus settles all 4 repos' pushes in one pass later)

## Known resume↔repo mismatch
"84 tests, 0 failures" — `tests/` contains only `HOW_IT_WORKS.txt`, zero real test files exist.
Unsupported until @senior-data-engineer builds real tests (deferred, see CLAUDE.md).
