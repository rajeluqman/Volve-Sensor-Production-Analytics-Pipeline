#!/usr/bin/env python3
"""
ML Model 3 — Anomaly Detection
Algorithm : Isolation Forest (unsupervised)
Label     : is_anomaly (evaluation only — NOT used in model.fit)
Source    : claudecatalog.gold.ml_feature_store
Tracking  : Databricks MLflow  (experiment: /Shared/volve_anomaly_detection)

contamination is set from the observed anomaly rate in the dataset so the
decision threshold matches real-world prevalence.
Evaluation uses is_anomaly (from CLAUDE.md rules) as ground truth.
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
MODEL_NAME      = "volve_anomaly_detection"
EXPERIMENT_PATH = f"/Shared/{MODEL_NAME}"

FEATURES = [
    "pressure_delta_24h",
    "water_cut_pct", "gas_oil_ratio",
    "pressure_7d_avg", "pressure_7d_std",
    "oil_vol_7d_avg", "water_cut_7d_avg",
    "BORE_OIL_VOL", "BORE_GAS_VOL", "ON_STREAM_HRS",
    "AVG_DOWNHOLE_PRESSURE", "AVG_WHP_P",
]
LABEL = "is_anomaly"

BASE_PARAMS = {
    "n_estimators": 200,
    "max_samples":  "auto",
    "random_state": 42,
    # contamination set dynamically from observed anomaly rate
}

SQL_LOAD = f"""
SELECT {', '.join(FEATURES + [LABEL, 'well_id', 'DATEPRD'])}
FROM {FEATURE_TABLE}
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
    print(f"  Loaded {len(df):,} rows")
    return df


def preprocess(df: pd.DataFrame):
    X = df[FEATURES].copy()
    y = df[LABEL].astype(int).copy()
    X = X.fillna(X.median(numeric_only=True))
    return X, y


def run():
    import mlflow
    import mlflow.sklearn
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import (
        precision_score, recall_score, f1_score, confusion_matrix,
    )

    print(f"\n{'='*60}")
    print(f"Model : {MODEL_NAME}")
    print(f"Algo  : Isolation Forest (unsupervised)")
    print(f"Label : {LABEL}  (evaluation only, not used in fit)")
    print(f"{'='*60}")

    with sql.connect(server_hostname=HOST, http_path=HTTP_PATH, access_token=TOKEN) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS claudecatalog.ml")

    df = load_features()
    X, y_true = preprocess(df)

    anomaly_rate  = float(y_true.mean())
    contamination = max(0.01, min(anomaly_rate, 0.5))
    print(f"  Observed anomaly rate : {anomaly_rate:.4f} → contamination={contamination:.4f}")

    params = {**BASE_PARAMS, "contamination": round(contamination, 4)}

    mlflow.set_tracking_uri("databricks")
    mlflow.set_experiment(EXPERIMENT_PATH)

    with mlflow.start_run(run_name=f"{MODEL_NAME}_iforest"):
        mlflow.log_params(params)
        mlflow.log_param("features",             len(FEATURES))
        mlflow.log_param("total_rows",           len(X))
        mlflow.log_param("observed_anomaly_rate", round(anomaly_rate, 4))

        model = IsolationForest(**params)
        model.fit(X)

        # Isolation Forest returns -1 for anomaly, +1 for normal → map to 0/1
        raw_preds = model.predict(X)
        y_pred    = (raw_preds == -1).astype(int)

        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall    = float(recall_score(y_true, y_pred, zero_division=0))
        f1        = float(f1_score(y_true, y_pred, zero_division=0))
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

        mlflow.log_metric("precision",        round(precision, 4))
        mlflow.log_metric("recall",           round(recall,    4))
        mlflow.log_metric("f1_score",         round(f1,        4))
        mlflow.log_metric("true_positives",   int(tp))
        mlflow.log_metric("false_positives",  int(fp))
        mlflow.log_metric("false_negatives",  int(fn))
        mlflow.log_metric("true_negatives",   int(tn))

        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X.iloc[:5],
            registered_model_name=f"claudecatalog.ml.{MODEL_NAME}",
        )

        print(f"\n  Results:")
        print(f"    Precision : {precision:.4f}")
        print(f"    Recall    : {recall:.4f}")
        print(f"    F1 Score  : {f1:.4f}")
        print(f"    TP={tp}  FP={fp}  FN={fn}  TN={tn}")
        print(f"\n  Logged to experiment : {EXPERIMENT_PATH}")
        print(f"  Model registered     : {MODEL_NAME}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
