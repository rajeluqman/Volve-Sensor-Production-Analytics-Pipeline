#!/usr/bin/env python3
"""
Bronze Layer — Orchestrator
Runs bronze_production and bronze_witsml in sequence (sequential, not parallel — 8GB RAM constraint).

Usage:
  python bronze/run_bronze.py              # run both
  python bronze/run_bronze.py --prod       # production only
  python bronze/run_bronze.py --witsml     # witsml only
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path

BRONZE_DIR = Path(__file__).parent
SCRIPTS = {
    "prod":   BRONZE_DIR / "bronze_production.py",
    "witsml": BRONZE_DIR / "bronze_witsml.py",
}


def run_script(name: str, path: Path) -> bool:
    print(f"\n{'#'*60}")
    print(f"# Running: {name}")
    print(f"{'#'*60}\n")
    t0 = time.time()
    result = subprocess.run([sys.executable, str(path)], check=False)
    elapsed = time.time() - t0
    ok = result.returncode == 0
    status = "PASSED" if ok else "FAILED"
    print(f"\n[{status}] {name} — {elapsed:.0f}s")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Bronze Layer Orchestrator")
    parser.add_argument("--prod",   action="store_true", help="Run production script only")
    parser.add_argument("--witsml", action="store_true", help="Run WITSML script only")
    args = parser.parse_args()

    run_prod   = args.prod   or (not args.prod and not args.witsml)
    run_witsml = args.witsml or (not args.prod and not args.witsml)

    results = {}
    t_start = time.time()

    if run_prod:
        results["bronze_production"] = run_script("bronze_production", SCRIPTS["prod"])

    if run_witsml:
        results["bronze_witsml"] = run_script("bronze_witsml", SCRIPTS["witsml"])

    total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Bronze Layer Summary — {total:.0f}s total")
    print(f"{'='*60}")
    all_passed = True
    for script, passed in results.items():
        icon = "OK" if passed else "FAIL"
        print(f"  [{icon}]  {script}")
        if not passed:
            all_passed = False

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
