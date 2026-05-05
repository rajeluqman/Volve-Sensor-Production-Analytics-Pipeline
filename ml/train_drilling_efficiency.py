#!/usr/bin/env python3
"""
ML Model 2 — Drilling Efficiency
Algorithm : Random Forest Regressor
Target    : rop_efficiency_score  (Sm3/hr per km wellbore depth)
Source    : claudecatalog.gold.ml_feature_store
Tracking  : Databricks MLflow  (experiment: /Shared/volve_drilling_efficiency)

Split strategy: time-based 80/20.
Feature importances logged as MLflow metrics for interpretability.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from databricks import sql

load_dotenv(Path(__file__).parent.parent / ".env")

HOST      = os.environ["DATABRICKS_HOST"].replace("https://", "")
HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
TOKEN     = os.environ["DATABRICKS_TOKEN"]

FEATURE_TABLE   = "claudecatalog.gold.ml_feature_store"
MODEL_NAME      = "volve_drilling_efficiency"
EXPERIMENT_PATH = f"/Shared/{MODEL_NAME}"

FEATURES = [
    "BORE_OIL_VOL", "BORE_GAS_VOL", "BORE_WAT_VOL", "ON_STREAM_HRS",
    "AVG_DOWNHOLE_PRESSURE", "AVG_WHP_P", "AVG_ANNULUS_PRESS",
    "water_cut_pct", "gas_oil_ratio",
    "pressure_7d_avg", "oil_vol_7d_avg", "water_cut_7d_avg",
    "pressure_30d_avg", "oil_vol_30d_avg",
    "pressure_7d_std", "oil_vol_7d_std",
    "cum_oil_vol", "cum_gas_vol",
    "total_md_m", "max_tvd_m", "avg_incl_deg", "avg_dls",
    "day_of_week", "month_num",
]
TARGET = "rop_efficiency_score"

PARAMS = {
    "n_estimators":    200,
    "max_depth":       8,
    "min_samples_leaf": 5,
    "n_jobs":          -1,
    "random_state":    42,
}

SQL_LOAD = f"""
SELECT {', '.join(FEATURES + [TARGET, 'well_id', 'DATEPRD'])}
FROM {FEATURE_TABLE}
WHERE {TARGET} IS NOT NULL
ORDER BY well_id, DATEPRD
"""


def load_features() -> pd.DataFrame:
    print(f"  Loading features from {FEATURE_TABLE}...")
    with sql.connect(server_hostname=HOST, http_path=HTTP_PATH, access_token=TOKEN) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_LOAD)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    print(f"  Loaded {len(df):,} rows, {df[TARGET].notna().sum():,} with valid target")
    return df


def preprocess(df: pd.DataFrame):
    X = df[FEATURES].copy()
    y = df[TARGET].copy()
    X = X.fillna(X.median(numeric_only=True))
    return X, y


def time_split(df: pd.DataFrame, X, y, train_frac=0.8):
    cutoff = int(len(df) * train_frac)
    return (
        X.iloc[:cutoff], X.iloc[cutoff:],
        y.iloc[:cutoff], y.iloc[cutoff:],
        df.iloc[cutoff:]["DATEPRD"].min(),
    )


def run():
    import mlflow
    import mlflow.sklearn
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    print(f"\n{'='*60}")
    print(f"Model : {MODEL_NAME}")
    print(f"Algo  : Random Forest Regressor")
    print(f"Target: {TARGET}")
    print(f"{'='*60}")

    with sql.connect(server_hostname=HOST, http_path=HTTP_PATH, access_token=TOKEN) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS claudecatalog.ml")

    df = load_features()
    X, y = preprocess(df)
    X_train, X_test, y_train, y_test, test_from = time_split(df, X, y)

    print(f"  Train rows : {len(X_train):,}")
    print(f"  Test rows  : {len(X_test):,}  (from {test_from})")

    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(EXPERIMENT_PATH)

    with mlflow.start_run(run_name=f"{MODEL_NAME}_rf"):
        mlflow.log_params(PARAMS)
        mlflow.log_param("features",       len(FEATURES))
        mlflow.log_param("train_rows",     len(X_train))
        mlflow.log_param("test_rows",      len(X_test))
        mlflow.log_param("split_strategy", "time_based_80_20")

        model = RandomForestRegressor(**PARAMS)
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        rmse  = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae   = float(mean_absolute_error(y_test, preds))
        r2    = float(r2_score(y_test, preds))

        mlflow.log_metric("rmse", round(rmse, 6))
        mlflow.log_metric("mae",  round(mae,  6))
        mlflow.log_metric("r2",   round(r2,   4))

        importances = (
            pd.Series(model.feature_importances_, index=FEATURES)
            .sort_values(ascending=False)
        )
        top5 = importances.head(5)
        for feat, imp in top5.items():
            mlflow.log_metric(f"feat_imp_{feat}", round(float(imp), 4))

        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X_train.iloc[:5],
            registered_model_name=f"claudecatalog.ml.{MODEL_NAME}",
        )

        print(f"\n  Results:")
        print(f"    RMSE : {rmse:.6f}")
        print(f"    MAE  : {mae:.6f}")
        print(f"    R²   : {r2:.4f}")
        print(f"\n  Top-5 features by importance:")
        for feat, imp in top5.items():
            print(f"    {feat:<30} {imp:.4f}")
        print(f"\n  Logged to experiment : {EXPERIMENT_PATH}")
        print(f"  Model registered     : {MODEL_NAME}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
