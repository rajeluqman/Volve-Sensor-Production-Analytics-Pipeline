#!/usr/bin/env python3
"""
ML Layer Orchestrator
Trains all 3 models in sequence, each logging to Databricks MLflow:
  1. volve_pressure_prediction   (XGBoost Regressor)
  2. volve_drilling_efficiency   (Random Forest Regressor)
  3. volve_anomaly_detection     (Isolation Forest)

Usage:
  python ml/run_ml.py
  python ml/run_ml.py --only pressure
  python ml/run_ml.py --only drilling
  python ml/run_ml.py --only anomaly
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import train_pressure_prediction
import train_drilling_efficiency
import train_anomaly_detection

ALL_STEPS = [
    ("pressure_prediction", train_pressure_prediction.run),
    ("drilling_efficiency", train_drilling_efficiency.run),
    ("anomaly_detection",   train_anomaly_detection.run),
]

KEY_MAP = {
    "pressure": "pressure_prediction",
    "drilling": "drilling_efficiency",
    "anomaly":  "anomaly_detection",
}


def main():
    parser = argparse.ArgumentParser(description="ML layer orchestrator")
    parser.add_argument(
        "--only",
        choices=list(KEY_MAP.keys()),
        default=None,
        help="Train only one model (default: train all three)",
    )
    args = parser.parse_args()

    if args.only:
        steps = [(n, fn) for n, fn in ALL_STEPS if n == KEY_MAP[args.only]]
    else:
        steps = ALL_STEPS

    print(f"\n{'#'*60}")
    print(f"  ML Layer — Training {len(steps)} model(s)")
    print(f"  (Trains locally in Codespaces, logs to Databricks MLflow)")
    print(f"{'#'*60}")

    overall_start = time.time()
    failed = []

    for name, fn in steps:
        t0 = time.time()
        try:
            fn()
            elapsed = time.time() - t0
            print(f"\n  [{name}] completed in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"\n  [{name}] FAILED after {elapsed:.1f}s — {e}", file=sys.stderr)
            failed.append(name)

    total = time.time() - overall_start
    print(f"\n{'#'*60}")
    if failed:
        print(f"  ML layer finished with ERRORS in: {', '.join(failed)}")
        print(f"  Total time: {total:.1f}s")
        print(f"{'#'*60}\n")
        sys.exit(1)
    else:
        print(f"  ML layer complete. Total time: {total:.1f}s")
        print(f"  View results: Databricks → Machine Learning → Experiments")
        print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()
