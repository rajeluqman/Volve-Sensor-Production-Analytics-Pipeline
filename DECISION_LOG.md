# DECISION_LOG.md — Volve Sensor & Production Analytics Pipeline (governance retrofit)

- **2026-06-29 — Stub directories flagged, not deleted.** `ingestion/nifi/` (NiFi+S3+Groovy)
  and `bronze/glue_jobs/` (AWS Glue) are `HOW_IT_WORKS.txt`-only stubs from the architecture
  documented as abandoned by `docs/ARCHITECTURE.md` ADR-001 — they reference scripts that were
  never built. Owner decision: flag everywhere a reader would be misled (CLAUDE.md, ADR-001,
  `tests/boundary_contract.py` exclusion comment), do not delete. Rationale: per the porting
  effort's standing hard rule (set after home-credit's `pipeline_dag.py` deletion), never
  remove code/files unilaterally — present evidence, ask first. Owner explicitly chose
  "flag, don't delete" for this case (not asked again per-file, ruling applies to both stub
  dirs and the parallel `tests/`/`data_quality/` emptiness finding).
- **2026-06-29 — Missing tests/GE suites: documented, NOT built in this pass.** `tests/` and
  `data_quality/` contain only `HOW_IT_WORKS.txt`. README's "Phase 7: Data Quality — Done" and
  the resume's "84 tests, 0 failures" are unsupported. Owner decision: document + flag the gap
  in `CLAUDE.md`/`INTERVIEW_GUIDE.md`/agent personas now; correct the README claims now;
  defer actually building the real test/GE-suite files to a future session once the
  governance+learning layer (this retrofit) is in place — building it now would be pipeline
  build scope, not governance retrofit scope (per `02_SONNET_BUILD_KICKOFF.md`'s "you add
  governance, not infrastructure" boundary).
- **2026-06-29 — 7 inline ADRs migrated, not reconstructed.** `docs/ARCHITECTURE.md` §6
  already contained real, contemporaneous rationale for 7 decisions (NiFi/Glue skip, SQL
  Warehouse only, WITSML JSON serialization, Delta Lake, 3-well scope, Docker Airflow, Excel
  header workaround) — these were promoted verbatim to `docs/ADR/ADR-001` through `ADR-007`,
  NOT tagged "(reconstructed)" since the rationale wasn't invented by this retrofit, just
  relocated and given proper ADR numbering. This corrects `01_OPUS_DECISIONS.md`'s "Volve = 0
  ADRs (repo-wide code search)" finding — the search apparently didn't catch ADRs embedded
  inside a non-`docs/ADR/` markdown file; Volve actually had decent decision-record coverage,
  just badly organized.
- **2026-06-29 — ADR-008 (identity grain) and ADR-009 (ML model selection) are new.** ADR-008
  is NOT reconstructed — written from direct code reading, the grain logic is observable fact.
  ADR-009 IS tagged "(reconstructed — owner confirm)" — no contemporaneous deliberation for
  WHY these 3 specific algorithms was found anywhere; the rationale given is inferred standard
  practice, flagged for the owner to confirm or replace.
- **2026-06-29 — README "Phase 7" corrected from "Done" to reflect the inline-SQL DQ gate
  reality; "Phase 9" left as "In Progress"** (it was already accurate — verified, not silently
  rounded up).
