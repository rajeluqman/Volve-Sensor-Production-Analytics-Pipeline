# Learning Curriculum — Volve Sensor & Production Analytics Pipeline

> Owned by @cikgu. The learning PATH for this project: each module pairs a concept with the
> real artifact that embodies it, the WHY-before-HOW questions you must answer first, and a DIY
> build task. Teach in order; close each module with a `LEARNING_LOG.md` entry.
> Run @cikgu as a MAIN session (not a subagent) for actual teaching. English-first per CIL's
> ADR-011 addendum (Manglish only if explicitly requested in-session).

**Score:** start 100. Track in `LEARNING_LOG.md`. Hint = -5. < 60 forces a docs break.

| # | Module | You must be able to answer (WHY) | Artifact (read AFTER you've tried) | DIY |
|---|--------|----------------------------------|-------------------------------------|-----|
| **M0** | The domain & the goal, and the doc trap | Why is anomaly detection + pressure prediction a production-analytics problem, not just "load Excel into a warehouse"? Why does this repo have `docs/BRD.md`/`DRD.md`/`DQD.md`/`PIPELINE_SPEC.md` describing a NiFi+Glue design that was never built? | `README.md`, `docs/ARCHITECTURE.md` ADR-001, `CLAUDE.md` "Known doc staleness" | spot 2 more stale claims in `docs/DRD.md` beyond the ones already flagged |
| **M1** | Databricks Volume + Delta Share ingestion | Why does this repo skip S3/NiFi/Glue entirely and read straight from a Databricks Volume? What is `read_files()` actually doing? | `bronze/bronze_production.py`, `docs/ADR/ADR-001-skip-nifi-glue-ingestion.md` | trace one Excel row from the Volume path to a Bronze table row, citing the script |
| **M2** | The Excel header workaround | Why does `read_files(format='excel')` return `_c0`, `_c1`... instead of real column names? What's the ADR-007 fix, and what would break without it? | `bronze/bronze_production.py`, `docs/ADR/ADR-007-excel-header-workaround.md` | reproduce the alias mapping for 5 columns from scratch, diff vs the real script |
| **M3** | WITSML JSON serialization | Why store `trajectoryStation` as a JSON string in Bronze instead of a native struct? What Spark/SQL error does this avoid? | `bronze/bronze_witsml.py`, `docs/ADR/ADR-003-witsml-json-serialization.md` | explain `INCOMPATIBLE_COLUMN_TYPE` in your own words before reading the ADR |
| **M4** | Silver grain — production dedup | Why `ROW_NUMBER() OVER (PARTITION BY WELL_BORE_CODE, DATEPRD ORDER BY ingestion_ts DESC)`? What happens to the pipeline's idempotency if you remove `ORDER BY ingestion_ts DESC`? | `silver/silver_production.py`, `docs/ADR/ADR-008-identity-grain.md` | write the dedup window from scratch DIY, then diff vs the real query |
| **M5** | Silver grain — trajectory explode | Why explode `trajectory_stations_json` into one row per survey station instead of keeping it nested? What grain does this produce, and why is it different from the production grain? | `silver/silver_trajectory.py`, `docs/DATA_MODEL.md` | name the trajectory grain in one sentence before opening the file |
| **M6** | Gold — no dbt, no SCD | Why does this repo NOT use dbt or SCD2, unlike home-credit/olist/paysim? What domain reason makes full `CREATE TABLE AS` rebuild acceptable here? | `gold/gold_production_daily.py`, `docs/ADR/ADR-008-identity-grain.md` | list 2 anomaly flags and their exact SQL condition from memory, then verify against the file |
| **M7** | ML feature store + model choice | Why lag(1/2/3/7d) + rolling-stat features for 3 different targets? Why Isolation Forest (unsupervised) for anomaly but XGBoost/RF (supervised) for the other two? | `gold/gold_ml_features.py`, `ml/train_*.py`, `docs/ADR/ADR-009-ml-model-selection.md` (reconstructed — confirm/replace the rationale yourself) | propose your OWN rationale for the RF-vs-XGBoost choice on drilling efficiency before reading the ADR's reconstructed guess |
| **M8** | The fake DQ gate | Why does the README/DQD.md describe 4 Great Expectations suites that don't exist? What's the REAL DQ gate, and where does it actually run? | `airflow/dags/volve_daily_pipeline.py` `DQ_CHECKS_SQL`, `data_quality/HOW_IT_WORKS.txt` (the stub) | write 1 new inline SQL DQ check in the same style, explain why it belongs in the DAG not a GE suite |
| **M9** | Airflow DAG + Slack backfill | Why does `list >> list` not work in Airflow 2.x, and how does this DAG's manual fan-out work around it? Why is Slack wired only on `on_failure_callback`? | `airflow/dags/volve_daily_pipeline.py`, the Slack backfill added by this retrofit | DIY a parse-clean single-task DAG with a graceful-degrade failure callback |
| **M10** | Snowflake serving | Why truncate+reload instead of incremental MERGE for the Snowflake load? Why is Snowflake never allowed to run transform logic here? | `snowflake/load_snowflake.py`, `snowflake/create_views.py`, `docs/ARCHITECTURE.md` | trace one Gold row to a Snowflake BI view, citing each script |
| **M11** | CI/CD & honest resume claims | Why does "84 tests, 0 failures" fail `INTERVIEW_GUIDE.md`'s evidence check? What's the actual gap, and what would it take to make the claim true? | `.github/workflows/ci.yml`, `tests/*_contract.py`, `INTERVIEW_GUIDE.md` | DIY: write 1 real pytest test for `silver_production.py`'s dedup logic — the FIRST real test in this repo |

## How a module runs (the ritual)
1. @cikgu poses the WHY questions. You answer from reasoning — NO reading yet.
2. You sketch the solution shape (mental model first, syntax last).
3. THEN you open the artifact and compare to your reasoning.
4. For DIY modules: @cikgu writes a `learning/diy/TICKET_<name>.md`; you build in
   `learning/diy/`; diff vs the real file line-by-line; quiz WHY on every gap.
5. LEARNING_LOG entry + score update.

## Suggested order
M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8 (face the doc-honesty gap early) → M9 → M10 → M11.

## Special note for this repo
M0, M8, and M11 are unique to Volve among the 4 retrofit repos: this is the only one where the
curriculum itself teaches "how to notice your own docs lied to you" as a first-class module,
not a footnote — because the gap here (NiFi/Glue/GE stubs, empty tests/) is real and large.
