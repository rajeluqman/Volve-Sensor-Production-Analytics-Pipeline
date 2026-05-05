#!/usr/bin/env python3
"""
ML Scoring — Batch Inference
Source  : claudecatalog.gold.ml_feature_store
Output  : claudecatalog.gold.ml_predictions
Models  : claudecatalog.ml.{volve_pressure_prediction,
                             volve_drilling_efficiency,
                             volve_anomaly_detection}

Loads the latest registered model version from Databricks MLflow for each model,
scores the feature store, and writes predictions to the Gold layer.

Usage:
  python ml/score_models.py
  python ml/score_models.py --days 30
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from databricks import sql
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

HOST      = os.environ["DATABRICKS_HOST"].replace("https://", "")
HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
TOKEN     = os.environ["DATABRICKS_TOKEN"]

FEATURE_TABLE     = "claudecatalog.gold.ml_feature_store"
PREDICTIONS_TABLE = "claudecatalog.gold.ml_predictions"

# Feature sets mirror the training scripts exactly
PRESSURE_FEATURES = [
    "pressure_lag1", "pressure_lag2", "pressure_lag3", "pressure_lag7",
    "pressure_7d_avg", "pressure_30d_avg", "pressure_7d_std",
    "water_cut_pct", "gas_oil_ratio", "water_cut_lag1", "gor_lag1",
    "BORE_OIL_VOL", "BORE_GAS_VOL", "BORE_WAT_VOL", "ON_STREAM_HRS",
    "AVG_WHP_P", "AVG_ANNULUS_PRESS",
    "day_of_week", "month_num",
    "total_md_m", "max_tvd_m",
    "cum_oil_vol",
]

DRILLING_FEATURES = [
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

ANOMALY_FEATURES = [
    "pressure_delta_24h",
    "water_cut_pct", "gas_oil_ratio",
    "pressure_7d_avg", "pressure_7d_std",
    "oil_vol_7d_avg", "water_cut_7d_avg",
    "BORE_OIL_VOL", "BORE_GAS_VOL", "ON_STREAM_HRS",
    "AVG_DOWNHOLE_PRESSURE", "AVG_WHP_P",
]

MODELS = [
    {
        "key":        "pressure",
        "registry":   "claudecatalog.ml.volve_pressure_prediction",
        "features":   PRESSURE_FEATURES,
        "output_col": "pred_next_day_pressure",
    },
    {
        "key":        "drilling",
        "registry":   "claudecatalog.ml.volve_drilling_efficiency",
        "features":   DRILLING_FEATURES,
        "output_col": "pred_rop_efficiency_score",
    },
    {
        "key":        "anomaly",
        "registry":   "claudecatalog.ml.volve_anomaly_detection",
        "features":   ANOMALY_FEATURES,
        "output_col": "pred_is_anomaly",
    },
]

# Union of all feature columns needed from the feature store
ALL_FEATURE_COLS = list(
    dict.fromkeys(PRESSURE_FEATURES + DRILLING_FEATURES + ANOMALY_FEATURES)
)

SQL_CREATE_PREDICTIONS = f"""
CREATE TABLE IF NOT EXISTS {PREDICTIONS_TABLE} (
    well_id                   STRING,
    DATEPRD                   DATE,
    pred_next_day_pressure    DOUBLE,
    pred_rop_efficiency_score DOUBLE,
    pred_is_anomaly           INT,
    scored_at                 TIMESTAMP
)
USING DELTA
COMMENT 'ML batch predictions — scored by Airflow run_ml_scoring task'
PARTITIONED BY (well_id)
"""


def load_features(conn, days: int) -> pd.DataFrame:
    cols = ", ".join(ALL_FEATURE_COLS + ["well_id", "DATEPRD"])
    query = f"""
    SELECT {cols}
    FROM   {FEATURE_TABLE}
    WHERE  DATEPRD >= DATE_SUB(CURRENT_DATE(), {days})
    ORDER BY well_id, DATEPRD
    """
    print(f"  Loading last {days} days from {FEATURE_TABLE}...")
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=col_names)
    print(f"  Loaded {len(df):,} rows — wells: {sorted(df['well_id'].unique())}")
    return df


def score_one_model(model_cfg: dict, df: pd.DataFrame) -> pd.Series:
    import mlflow.pyfunc

    uri = f"models:/{model_cfg['registry']}/latest"
    print(f"  Loading model: {uri}")
    model = mlflow.pyfunc.load_model(uri)

    X = df[model_cfg["features"]].copy()
    X = X.fillna(X.median(numeric_only=True))

    preds = model.predict(X)
    return pd.Series(preds, index=df.index, name=model_cfg["output_col"])


def write_predictions(conn, df: pd.DataFrame, scored_at: str) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS claudecatalog.gold")
        cur.execute(SQL_CREATE_PREDICTIONS)
        # Remove existing predictions for the same date window before inserting
        min_date = str(df["DATEPRD"].min())
        cur.execute(
            f"DELETE FROM {PREDICTIONS_TABLE} WHERE DATEPRD >= '{min_date}'"
        )

    output_cols = ["well_id", "DATEPRD",
                   "pred_next_day_pressure", "pred_rop_efficiency_score",
                   "pred_is_anomaly"]
    for col in output_cols[2:]:
        if col not in df.columns:
            df[col] = None

    rows = []
    for _, row in df.iterrows():
        pressure = float(row["pred_next_day_pressure"]) if pd.notna(row["pred_next_day_pressure"]) else None
        drilling = float(row["pred_rop_efficiency_score"]) if pd.notna(row["pred_rop_efficiency_score"]) else None
        anomaly  = int(row["pred_is_anomaly"]) if pd.notna(row["pred_is_anomaly"]) else None
        rows.append((str(row["well_id"]), str(row["DATEPRD"]), pressure, drilling, anomaly, scored_at))

    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {PREDICTIONS_TABLE} VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
    print(f"  Written {len(rows):,} rows to {PREDICTIONS_TABLE}")


def run(days: int = 30) -> None:
    import mlflow

    print(f"\n{'='*60}")
    print(f"ML Scoring — Batch Inference")
    print(f"Source  : {FEATURE_TABLE}")
    print(f"Output  : {PREDICTIONS_TABLE}")
    print(f"Window  : last {days} days")
    print(f"{'='*60}")

    mlflow.set_tracking_uri("databricks")
    scored_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with sql.connect(server_hostname=HOST, http_path=HTTP_PATH, access_token=TOKEN) as conn:
        df = load_features(conn, days)

        if df.empty:
            print("  No feature data found — skipping scoring")
            return

        failed_models = []
        for model_cfg in MODELS:
            try:
                preds = score_one_model(model_cfg, df)
                df[model_cfg["output_col"]] = preds
                print(f"  [{model_cfg['key']}] scored {len(preds):,} rows")
            except Exception as e:
                print(f"  [{model_cfg['key']}] SKIP — {e}", file=sys.stderr)
                df[model_cfg["output_col"]] = None
                failed_models.append(model_cfg["key"])

        write_predictions(conn, df, scored_at)

    # Summary
    anomaly_col = "pred_is_anomaly"
    if anomaly_col in df.columns:
        n_anomalies = int(df[anomaly_col].eq(1).sum())
        print(f"\n  Anomalies flagged : {n_anomalies} / {len(df)}")

    if failed_models:
        print(f"  Models skipped    : {', '.join(failed_models)}", file=sys.stderr)

    print(f"\n  Scored at : {scored_at}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="ML batch scoring — Volve pipeline")
    parser.add_argument("--days", type=int, default=30,
                        help="Score last N days from feature store (default: 30)")
    args = parser.parse_args()
    run(args.days)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
