# Start Here — Volve Sensor & Production Analytics Pipeline

This space mirrors the repo's real documentation, including its known staleness. Read in this
order:

1. **README.md** — project overview, real stack, build status
2. **CLAUDE.md** — AI/governance context; "Known doc staleness" section is the single most
   important thing to read before trusting any other doc in this set
3. **docs/ARCHITECTURE.md** (v2.0) — the doc-of-record for stack/architecture
4. **docs/DATA_MODEL.md** + **docs/DATA_DICTIONARY.md** — grain doctrine, column reference
5. **docs/ADR/** — ADR-001 through ADR-007 (migrated from ARCHITECTURE.md §6, real
   contemporaneous rationale), ADR-008 (identity grain, new), ADR-009 (ML model selection,
   reconstructed — flagged for owner confirmation)
6. **docs/BRD.md, DRD.md, PIPELINE_SPEC.md, DQD.md** — kept for historical reference, all
   **stale v1.0**, describe an abandoned NiFi+AWS Glue+Great Expectations design. Cross-check
   anything from these against ARCHITECTURE.md or the real code before relying on it.
7. **INTERVIEW_GUIDE.md** — resume-claim ↔ repo-evidence reconciliation
8. **PROJECT_STATUS.md** — current build state

Synced via `scripts/sync_docs_to_confluence.py` (manual run, not CI-wired).
