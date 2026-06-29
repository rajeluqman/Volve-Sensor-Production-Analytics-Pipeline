#!/usr/bin/env python3
"""Reset the SIM lab to clean baseline — re-seed + re-build sim only. Never hand-patched.

Usage: python simulation/faults/reset.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "simulation"


def main() -> int:
    print("[reset] this is a stub until simulation/ has real synthetic sim_ fixtures + a build target.")
    print("[reset] intended sequence: regenerate sim synthetic Excel/WITSML fixtures -> "
          "rebuild sim_catalog.bronze/silver/gold via the real scripts pointed at sim_ tables "
          "-> python simulation/check_isolation.py (no dbt step — this repo has none, ADR-008)")
    result = subprocess.run([sys.executable, str(SIM / "check_isolation.py")])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
