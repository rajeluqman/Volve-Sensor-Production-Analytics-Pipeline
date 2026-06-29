# DATA_DICTIONARY.md
## Volve Sensor & Production Analytics Pipeline

> NEW doc (previously missing entirely — flagged by `01_OPUS_DECISIONS.md`). Written
> 2026-06-29 from direct code reading. Source-system column names (UPPERCASE) are preserved
> per `docs/ARCHITECTURE.md` §8 naming convention; derived columns are snake_case.

## `silver.cleaned_production`

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `DATEPRD` | DATE | Excel `DATEPRD`, format `dd-MMM-yy` | grain key (with `well_id`) |
| `WELL_BORE_CODE` | STRING | Excel | raw well-bore identifier |
| `well_id` | STRING | derived (regex `F-[0-9]+` from `WELL_BORE_CODE`) | grain key, locked to F-1/F-11/F-12 (ADR-005) |
| `ON_STREAM_HRS` | DOUBLE | Excel, `TRY_CAST` | hours on production, 0–24 expected |
| `AVG_DOWNHOLE_PRESSURE` | DOUBLE | Excel, `TRY_CAST` | psi |
| `AVG_DOWNHOLE_TEMPERATURE` | DOUBLE | Excel, `TRY_CAST` | |
| `BORE_OIL_VOL` | DOUBLE | Excel | daily oil Sm³ |
| `BORE_GAS_VOL` | DOUBLE | Excel | daily gas Sm³ |
| `BORE_WAT_VOL` | DOUBLE | Excel | daily water Sm³ |
| `water_cut_pct` | DOUBLE | derived: `BORE_WAT_VOL / (BORE_OIL_VOL + BORE_WAT_VOL) * 100` | 0–100 expected |
| `gas_oil_ratio` | DOUBLE | derived: `BORE_GAS_VOL / BORE_OIL_VOL` | NULL if oil = 0 |
| `is_zero_prod_uptime` | BOOLEAN | derived | `BORE_OIL_VOL = 0 AND ON_STREAM_HRS > 0` |
| `is_pressure_valid` | BOOLEAN | derived | `AVG_DOWNHOLE_PRESSURE BETWEEN 0 AND 10000` |
| `ingestion_ts` | TIMESTAMP | Bronze metadata | used for dedup `ROW_NUMBER()` ordering |
| `date_year` | INT | derived | partition column |

## `silver.cleaned_trajectory`

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `well_id` | STRING | Bronze metadata | grain key |
| `md_m` | DOUBLE | `station.md._VALUE`, `TRY_CAST` | measured depth, metres; grain key |
| `md_uom` | STRING | `station.md._uom` | unit of measure, expected `m` |
| `incl_deg` | DOUBLE | `station.incl._VALUE`, `TRY_CAST` | inclination, degrees, 0–180 expected |
| `azi_deg` | DOUBLE | `station.azi._VALUE`, `TRY_CAST` | azimuth, degrees, 0–360 expected |
| `tvd_m`, `disp_ns_m`, `disp_ew_m` | DOUBLE | station struct fields | true vertical depth, N/S and E/W displacement |
| `is_md_valid`, `is_incl_valid`, `is_azi_valid` | BOOLEAN | derived | range-check quality flags |

## `gold.production_daily`

All `silver.cleaned_production` columns, plus:

| Column | Type | Notes |
|--------|------|-------|
| `pressure_delta_24h` | DOUBLE | `pressure - LAG(pressure, 1) OVER (PARTITION BY well_id ORDER BY DATEPRD)` |
| `oil_vol_7d_avg`, `gas_vol_7d_avg`, `wat_vol_7d_avg`, `pressure_7d_avg`, `water_cut_7d_avg` | DOUBLE | `AVG(...) OVER (PARTITION BY well_id ORDER BY DATEPRD ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)` — verified `gold/gold_production_daily.py:77-81` |
| `oil_vol_30d_avg`, `gas_vol_30d_avg`, `pressure_30d_avg`, `water_cut_30d_avg` | DOUBLE | same pattern, 29 PRECEDING — verified `gold/gold_production_daily.py:84-87` |
| `cum_oil_vol_monthly`, `cum_gas_vol_monthly` | DOUBLE | monthly cumulative, resets each calendar month — verified `gold/gold_production_daily.py:89-99` |
| `is_anomaly_pressure` | BOOLEAN | `pressure_delta_24h > 500` |
| `is_water_cut_spike` | BOOLEAN | `water_cut_pct > 80 AND LAG(water_cut_pct) < 60` |
| `is_gor_anomaly` | BOOLEAN | `gas_oil_ratio > 3 * well_baseline_gor` |

## `gold.ml_feature_store`

Lag features (1/2/3/7 day) and rolling stats over the Silver production columns, built for the
3 ML targets: `next_day_pressure`, `rop_efficiency_score`, `is_anomaly`. See
`gold/gold_ml_features.py` for the full column list — not exhaustively re-typed here to avoid
drift; read the script directly before asserting a specific feature name exists.

## Source data dictionary (raw Excel, pre-Silver)

See `docs/DRD.md` §2 for the raw column list — that section's column names ARE accurate (the
staleness in DRD.md is about the ingestion architecture/source-count, not the production Excel
schema, which hasn't changed).
