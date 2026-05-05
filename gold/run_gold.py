#!/usr/bin/env python3
"""
Gold Layer Orchestrator
Runs both gold scripts in sequence:
  1. gold_production_daily  → claudecatalog.gold.production_daily
  2. gold_ml_features       → claudecatalog.gold.ml_feature_store

Usage:
  python gold/run_gold.py
  python gold/run_gold.py --only daily
  python gold/run_gold.py --only features
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import gold_production_daily
import gold_ml_features


def main():
    parser = argparse.ArgumentParser(description="Gold layer orchestrator")
    parser.add_argument(
        "--only",
        choices=["daily", "features"],
        default=None,
        help="Run only one script (default: run both)",
    )
    args = parser.parse_args()

    steps = []
    if args.only is None or args.only == "daily":
        steps.append(("production_daily", gold_production_daily.run))
    if args.only is None or args.only == "features":
        steps.append(("ml_feature_store", gold_ml_features.run))

    print(f"\n{'#'*60}")
    print(f"  Gold Layer — Running {len(steps)} script(s)")
    print(f"{'#'*60}")

    overall_start = time.time()
    failed = []

    for name, fn in steps:
        t0 = time.time()
        try:
            fn()
            elapsed = time.time() - t0
            print(f"  [{name}] completed in {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  [{name}] FAILED after {elapsed:.1f}s — {e}", file=sys.stderr)
            failed.append(name)

    total = time.time() - overall_start
    print(f"\n{'#'*60}")
    if failed:
        print(f"  Gold layer finished with ERRORS in: {', '.join(failed)}")
        print(f"  Total time: {total:.1f}s")
        print(f"{'#'*60}\n")
        sys.exit(1)
    else:
        print(f"  Gold layer complete. Total time: {total:.1f}s")
        print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()
