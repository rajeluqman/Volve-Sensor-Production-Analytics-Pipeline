#!/usr/bin/env python3
"""
Silver Layer — Orchestrator
Runs both Silver scripts in sequence.
Run: python silver/run_silver.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

SCRIPTS = [
    ("Production", ROOT / "silver" / "silver_production.py"),
    ("Trajectory", ROOT / "silver" / "silver_trajectory.py"),
]


def run():
    print("\n" + "=" * 60)
    print("Silver Layer — Full Run")
    print("=" * 60)

    for name, script in SCRIPTS:
        print(f"\n>>> Running {name} ({script.name})...")
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
        )
        if result.returncode != 0:
            print(f"\nFAILED: {script.name} exited with code {result.returncode}")
            sys.exit(result.returncode)

    print("\n" + "=" * 60)
    print("Silver Layer — All scripts completed successfully.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run()
