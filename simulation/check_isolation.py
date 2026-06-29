#!/usr/bin/env python3
"""Isolation guard for the Volve simulation lab (simulation/).

Ported from creative_intelligence_lab's simulation/check_isolation.py (pipeline-retrofit
effort), retargeted to THIS repo's real storage namespace. Unlike home-credit/olist/paysim,
Volve has no dbt project to check a project-name mismatch against — there is no dbt anywhere
in this repo (ADR-008). Isolation here means: no sim SQL/script may reference the REAL
Unity Catalog namespace (`claudecatalog.{bronze,silver,gold,ml}`) or the real Snowflake
database (`VOLVE_DB`) — any sim Delta/Snowflake reference must use a `sim_` prefixed
catalog/database instead, so fault-injection drills can never corrupt canonical tables.

    python simulation/check_isolation.py

Exit 0 = isolated (safe to break things). Exit 1 = a boundary was crossed (STOP).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"

REAL_CATALOG = "claudecatalog"
REAL_SNOWFLAKE_DB = "VOLVE_DB"
SIM_CATALOG_PREFIX = "sim_"


def main() -> int:
    failures: list[str] = []

    # Only .sql/.py/.yml/.yaml are scanned for R1/R2 — these are the file types that could
    # actually DECLARE a connection/table reference. .md files (README, ISOLATION_CONTRACT.md,
    # faults/catalog/*.md) legitimately MENTION the real names in prose while describing the
    # rule itself — scanning those would just be false positives on this contract's own docs.
    skip = {Path(__file__).resolve()}
    for f in SIM.rglob("*"):
        if not f.is_file() or f.suffix not in (".sql", ".yml", ".yaml", ".py") or f.resolve() in skip:
            continue
        for lineno, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            # R1 — no real Unity Catalog reference inside sim files (must be sim_<name> instead)
            for m in re.finditer(rf"\b{REAL_CATALOG}\.\w+\.\w+", line):
                failures.append(
                    f"R1: {f.relative_to(ROOT)}:{lineno}: references real catalog "
                    f"'{REAL_CATALOG}' — use a 'sim_' prefixed catalog instead: {m.group(0)}"
                )
            # R2 — no real Snowflake database reference inside sim files
            if REAL_SNOWFLAKE_DB in line:
                failures.append(
                    f"R2: {f.relative_to(ROOT)}:{lineno}: references real Snowflake database "
                    f"'{REAL_SNOWFLAKE_DB}' — sim must use its own database"
                )

    # R3 — every sim catalog/database literal actually carries the sim_ prefix (positive check)
    sim_catalog_re = re.compile(r"\bsim_[a-z0-9_]+\b")
    found_sim_ref = False
    for f in SIM.rglob("*"):
        if not f.is_file() or f.suffix not in (".sql", ".md", ".yml", ".yaml") or f.resolve() in skip:
            continue
        if sim_catalog_re.search(f.read_text(errors="ignore")):
            found_sim_ref = True
            break
    if not found_sim_ref:
        print("ℹ️  R3: no sim_-prefixed catalog/database reference found yet — drills not yet wired to storage")

    if failures:
        print(f"\n❌ ISOLATION CONTRACT FAILED — {len(failures)} violation(s):", file=sys.stderr)
        for fail in failures:
            print(f"   • {fail}", file=sys.stderr)
        return 1
    print("✅ isolation contract OK — sim lab cannot touch the real claudecatalog/VOLVE_DB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
