# DATA_MODEL.md — Grain & Table Doctrine
## Volve Sensor & Production Analytics Pipeline

> NEW doc (previously missing entirely — flagged by `01_OPUS_DECISIONS.md`). Written
> 2026-06-29 from direct code reading (`bronze/`, `silver/`, `gold/`), cross-checked against
> `docs/ARCHITECTURE.md` v2.0. Governs alongside ADR-008.

## 1. Tables & grain

| Layer | Table | Grain | Built by |
|-------|-------|-------|----------|
| Bronze | `claudecatalog.bronze.raw_production` | 1 row per source Excel row (no dedup yet) | `bronze/bronze_production.py` |
| Bronze | `claudecatalog.bronze.raw_witsml_trajectory` | 1 row per trajectory XML file (stations nested as JSON, ADR-003) | `bronze/bronze_witsml.py` |
| Silver | `claudecatalog.silver.cleaned_production` | **(well_id, DATEPRD)** — 1 row per well per day | `silver/silver_production.py` |
| Silver | `claudecatalog.silver.cleaned_trajectory` | **(well_id, md_m)** — 1 row per survey station | `silver/silver_trajectory.py` |
| Gold | `claudecatalog.gold.production_daily` | (well_id, DATEPRD), same as Silver + KPIs/anomaly flags | `gold/gold_production_daily.py` |
| Gold | `claudecatalog.gold.ml_feature_store` | (well_id, DATEPRD), same grain + lag/rolling ML features | `gold/gold_ml_features.py` |
| Gold | `claudecatalog.gold.ml_predictions` | (well_id, DATEPRD), batch-scored | `ml/score_models.py` |
| ML registry | `claudecatalog.ml.{volve_pressure_prediction,volve_drilling_efficiency,volve_anomaly_detection}` | model artifact, not a data grain | `ml/train_*.py` |
| Serving | `VOLVE_DB.SERVING.production_daily`, `VOLVE_DB.SERVING.ml_predictions` | mirrors Gold grain, truncate+reload | `snowflake/load_snowflake.py` |

⚠️ Note: `docs/ARCHITECTURE.md` §1 names the Gold table `gold.production_kpis` — the real table
built by `gold/gold_production_daily.py` is `gold.production_daily`. This doc uses the real
table name; `docs/ARCHITECTURE.md` is flagged for that one drift but not rewritten in this pass.

## 2. No SCD, no dbt
See `docs/ADR/ADR-008-identity-grain.md` for the full rationale. In short: every Gold table is
rebuilt via `CREATE TABLE ... AS` on each pipeline run; there is no surrogate key, no
`is_current`/`valid_from`/`valid_to` columns anywhere in this repo, and no dbt project.

## 3. Derived columns (Silver)
| Column | Formula | Defined in |
|--------|---------|-----------|
| `water_cut_pct` | `BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100` | `silver/silver_production.py` |
| `gas_oil_ratio` | `BORE_GAS_VOL / BORE_OIL_VOL` | `silver/silver_production.py` |
| `well_id` | regex-extracted from `WELL_BORE_CODE` | `silver/silver_production.py` |
| `md_m`, `incl_deg`, `azi_deg` | `TRY_CAST(station.{md,incl,azi}._VALUE AS DOUBLE)` | `silver/silver_trajectory.py` |

## 4. Anomaly flags (Gold)
| Flag | Condition | Defined in |
|------|-----------|-----------|
| `is_anomaly_pressure` | `pressure_delta_24h > 500` (psi) | `gold/gold_production_daily.py` |
| `is_zero_prod_uptime` | `BORE_OIL_VOL = 0 AND ON_STREAM_HRS > 0` | `gold/gold_production_daily.py` |
| `is_water_cut_spike` | `water_cut_pct > 80 AND LAG(water_cut_pct) < 60` | `gold/gold_production_daily.py` |
| `is_gor_anomaly` | `gas_oil_ratio > 3 * well_baseline_gor` | `gold/gold_production_daily.py` |

## 5. Governance
@data-architect owns this doc and the grain doctrine (ADR-008). Any change to the
`gold_production_daily.py`/`gold_ml_features.py` SELECT lists that drops `well_id` or the date
column is caught by `tests/identity_contract.py` ID4.
