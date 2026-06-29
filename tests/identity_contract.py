#!/usr/bin/env python3
"""Identity contract — deterministic gate over the (well_id, DATEPRD) / (well_id, md_m) grain.

Ported from creative_intelligence_lab's tests/lineage_contract.py pattern (via the other 3
retrofit repos' "identity contract" rename) — this repo has NO dbt and NO SCD: Gold tables are
full `CREATE TABLE ... AS` rebuilds each run (ADR-008), so the grain guarantee to check is
"the dedup/explode logic that PRODUCES the grain is present in Silver", not a surrogate-key/
SCD2 column set the way home-credit/olist/paysim check it.

Two grains in this repo:
  - Production: (well_id, DATEPRD) — exactly 1 row per well per day from Silver onward.
    Enforced by silver/silver_production.py's ROW_NUMBER() OVER (PARTITION BY
    WELL_BORE_CODE, DATEPRD ORDER BY ingestion_ts DESC) dedup window.
  - Trajectory: (well_id, md_m) — one row per survey station, after exploding
    trajectory_stations_json. Enforced by silver/silver_trajectory.py.

Encodes @data-architect's grain guarantee statically, WITHOUT requiring a live Databricks
connection — it checks the SQL source, not warehouse data. Run the actual scripts against
Databricks for the runtime complement.

Stdlib only ($0, no deps). Exit 0 = contract holds. Exit 1 = hard violation.

Rules:
  ID1  silver/silver_production.py must dedup by (WELL_BORE_CODE, DATEPRD) via a
       ROW_NUMBER()/PARTITION BY window — a dropped PARTITION BY column is grain drift
  ID2  silver/silver_production.py must filter well_id to the 3 locked wells (F-1, F-11, F-12)
       — a missing filter would silently let a 4th well's rows through
  ID3  silver/silver_trajectory.py must explode/parse trajectory_stations_json into station-
       level rows (md/incl/azi columns) — losing this collapses the grain back to one row
       per trajectory file
  ID4  gold/gold_production_daily.py and gold/gold_ml_features.py must each select well_id AND
       a date column (DATEPRD or date_year) — catches a Gold script that silently drops the
       grain key

Run:  python tests/identity_contract.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SILVER_PRODUCTION = REPO / "silver" / "silver_production.py"
SILVER_TRAJECTORY = REPO / "silver" / "silver_trajectory.py"
GOLD_PRODUCTION = REPO / "gold" / "gold_production_daily.py"
GOLD_FEATURES = REPO / "gold" / "gold_ml_features.py"

LOCKED_WELLS = ("F-1", "F-11", "F-12")


def check() -> list[str]:
    errors: list[str] = []

    # ID1 + ID2 — Silver production dedup window + well filter
    if not SILVER_PRODUCTION.exists():
        errors.append(f"ID1: {SILVER_PRODUCTION.relative_to(REPO)} missing — Silver production transform not found")
    else:
        text = SILVER_PRODUCTION.read_text()
        if "ROW_NUMBER()" not in text:
            errors.append("ID1: ROW_NUMBER() dedup window not found in silver_production.py — grain dedup may have been removed")
        if not re.search(r"PARTITION BY\s+WELL_BORE_CODE\s*,\s*DATEPRD", text, re.IGNORECASE):
            errors.append("ID1: dedup window is not partitioned by (WELL_BORE_CODE, DATEPRD) — grain drift")
        for well in LOCKED_WELLS:
            if well not in text:
                errors.append(f"ID2: locked well '{well}' not found in silver_production.py — 3-well scope filter may have changed (ADR-005)")

    # ID3 — Silver trajectory explode/station columns
    if not SILVER_TRAJECTORY.exists():
        errors.append(f"ID3: {SILVER_TRAJECTORY.relative_to(REPO)} missing — Silver trajectory transform not found")
    else:
        text = SILVER_TRAJECTORY.read_text()
        for col in ("md", "incl", "azi"):
            if col not in text.lower():
                errors.append(f"ID3: survey-station column '{col}' not found in silver_trajectory.py — trajectory grain may have collapsed")

    # ID4 — Gold scripts keep the grain key
    for gold_path, label in ((GOLD_PRODUCTION, "gold_production_daily.py"), (GOLD_FEATURES, "gold_ml_features.py")):
        if not gold_path.exists():
            errors.append(f"ID4: {label} missing")
            continue
        text = gold_path.read_text()
        if "well_id" not in text:
            errors.append(f"ID4: {label} does not reference well_id — grain key dropped")
        if "DATEPRD" not in text and "date_year" not in text:
            errors.append(f"ID4: {label} does not reference DATEPRD/date_year — date grain key dropped")

    return errors


def main() -> int:
    errors = check()
    if errors:
        print(f"\n❌ IDENTITY CONTRACT FAILED — {len(errors)} violation(s):", file=sys.stderr)
        for e in errors:
            print(f"   • {e}", file=sys.stderr)
        print("\n   See docs/DATA_MODEL.md + docs/ADR/ADR-008-identity-grain.md. Fix before proceeding.",
              file=sys.stderr)
        return 1
    print("✅ identity contract OK ((well_id, DATEPRD) production grain, (well_id, md_m) trajectory grain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
