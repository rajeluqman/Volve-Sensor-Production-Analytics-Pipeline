# ADR-009: ML model selection — XGBoost / Random Forest / Isolation Forest

**Status:** Accepted (reconstructed — owner confirm rationale) | **Date:** 2026-06-29 (written by this retrofit)

> **(reconstructed — owner confirm)**: no contemporaneous deliberation for WHY these specific
> 3 algorithms (vs. alternatives) was found anywhere in the repo — `docs/PIPELINE_SPEC.md` §5
> and the README's "ML Models" table state the choice but not the reasoning. The rationale
> below is inferred from standard practice for each problem shape; the owner should confirm or
> replace it before this is cited as a deliberate engineering decision in an interview.

## Decision
Three MLflow-tracked models, each solving a different problem shape from the same Gold feature
store (`gold/gold_ml_features.py` → `claudecatalog.gold.ml_feature_store`):

| Model | Algorithm | Target | Problem shape |
|-------|-----------|--------|----------------|
| `volve_pressure_prediction` | XGBoost Regressor | `next_day_pressure` | regression, likely non-linear lag/rolling-feature interactions |
| `volve_drilling_efficiency` | Random Forest Regressor | `rop_efficiency_score` | regression, mixed sensor features (ROP/RPM/SWOB/SPPA/ECD) |
| `volve_anomaly_detection` | Isolation Forest | `is_anomaly` (binary) | unsupervised/semi-supervised outlier detection, no reliable labeled anomaly set at this data volume |

## Why (reconstructed)
- **XGBoost for pressure**: gradient-boosted trees handle the lag/rolling-window feature
  interactions (`gold_ml_features.py` lag 1/2/3/7d + rolling stats) well without manual
  feature-interaction engineering; standard first choice for tabular regression with engineered
  time-lag features.
- **Random Forest for drilling efficiency**: fewer features, more robust to the WITSML sensor
  noise (ROP/RPM/SWOB/SPPA/ECD) than a single tree, simpler to tune than XGBoost when the
  feature set is small — reasonable default, not confirmed as a deliberate trade-off vs.
  XGBoost here too.
- **Isolation Forest for anomaly detection**: the dataset has no ground-truth anomaly labels (3
  wells, ~5k rows) — Isolation Forest is unsupervised, doesn't need labeled anomalies, and is
  the standard choice when "anomaly" is rule-derived in Gold (`is_anomaly_pressure`,
  `is_water_cut_spike`, etc.) rather than independently labeled.

## Owner action item
Confirm or replace this rationale — in particular, why Random Forest over XGBoost for drilling
efficiency (the repo doesn't show a documented bake-off), and whether the anomaly labels used
for any supervised evaluation came from the Gold rule-flags (in which case the model is
partially circular — learning to reproduce a rule, not detecting independently).
