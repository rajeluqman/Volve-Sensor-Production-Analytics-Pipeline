#!/usr/bin/env python3
"""Inject a named, reversible fault into the SIM lab only (never touches real models).

Usage: python simulation/faults/inject.py <fault_id>   (F01-F04, see faults/README.md)
Guard: refuses to run if simulation/check_isolation.py would fail afterward.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "simulation"

FAULTS = {
    "F01": "Silver production dedup window loses ORDER BY ingestion_ts DESC — duplicate (well_id, DATEPRD) rows reappear — see faults/catalog/F01.md",
    "F02": "WITSML trajectory_stations_json explode skipped — trajectory grain collapses back to 1 row per file — see faults/catalog/F02.md",
    "F03": "Snowflake load truncate step skipped — stale rows persist alongside new load — see faults/catalog/F03.md",
    "F04": "3-well scope filter dropped (well_id IN ('F-1','F-11','F-12')) — a 4th well's rows leak through — see faults/catalog/F04.md",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in FAULTS:
        print(f"Usage: inject.py <{'|'.join(FAULTS)}>")
        return 1
    fault_id = argv[1]
    print(f"[inject] {fault_id}: {FAULTS[fault_id]}")
    print("[inject] apply the catalog steps manually against simulation/'s synthetic sim_ "
          "fixtures only, then re-run check_isolation.py before continuing.")
    result = subprocess.run([sys.executable, str(SIM / "check_isolation.py")])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
