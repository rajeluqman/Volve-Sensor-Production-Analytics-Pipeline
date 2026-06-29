#!/usr/bin/env python3
"""Governance hook — makes Claude check governed docs/ADRs BEFORE and AFTER touching governed
files. Ported from creative_intelligence_lab's hook of the same name (pipeline-retrofit
effort), retargeted to THIS repo's real files (Databricks SQL Warehouse Bronze/Silver/Gold
`.py` scripts, no dbt — unlike home-credit/olist/paysim).

Wired in .claude/settings.json for Edit|Write|MultiEdit:
  • PreToolUse  → inject a "STOP, read these docs first" reminder when the target file is
                  under governance (non-blocking context nudge).
  • PostToolUse → auto-run the matching contract test(s) after the edit; exit 2 with the
                  failure so Claude is FORCED to see and fix it (hard block).

Three contracts, two owners (CLAUDE.md governance axes):
  - tests/identity_contract.py  — @data-architect, (well_id, DATEPRD) / (well_id, md_m) grain
  - tests/boundary_contract.py  — @scope-guardian (Databricks SQL Warehouse only, no Glue/
                                   NiFi/PySpark cluster/dbt, 3-well scope, Snowflake serving-only)
  - tests/doc_reference_contract.py — @documentation-sherpa (no path drift in docs/ADR)

Stdlib only. Never crashes the tool call on its own bug (any internal error → exit 0).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

IDENTITY_MSG = (
    "Production grain = (well_id, DATEPRD), exactly 1 row per well per day from Silver onward "
    "(silver/silver_production.py dedup). Trajectory grain = (well_id, md_m), one row per "
    "survey station after exploding trajectory_stations_json. ADR-008 + docs/DATA_MODEL.md."
)
BOUNDARY_MSG = (
    "All transform compute = Databricks SQL Warehouse only (no PySpark cluster, no Glue, no "
    "NiFi — those dirs are orphaned stubs). 3 wells only (F-1, F-11, F-12). No dbt in this "
    "repo. Snowflake = serving veneer only. docs/ARCHITECTURE.md."
)
GRAIN_MSG = "No-dbt, no-SCD doctrine: Gold = full CREATE TABLE AS rebuild each run, not MERGE. ADR-008."

# (path substring, docs to cite, reminder message, contract scripts to run post-edit)
RULES: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("gold/gold_production_daily.py", "ADR-008 + docs/DATA_MODEL.md", GRAIN_MSG, ("identity_contract.py", "doc_reference_contract.py")),
    ("gold/gold_ml_features.py", "ADR-008 + docs/DATA_MODEL.md", GRAIN_MSG, ("identity_contract.py", "doc_reference_contract.py")),
    ("silver/silver_production.py", "ADR-008 grain doctrine", IDENTITY_MSG, ("identity_contract.py",)),
    ("silver/silver_trajectory.py", "ADR-008 grain doctrine", IDENTITY_MSG, ("identity_contract.py",)),
    ("ml/train_", "ADR-009 ML model selection (reconstructed)", GRAIN_MSG, ("doc_reference_contract.py",)),
    ("airflow/dags/volve_daily_pipeline.py", "docs/ARCHITECTURE.md + 3-well scope (ADR-005)", BOUNDARY_MSG, ("boundary_contract.py",)),
    ("snowflake/", "docs/ARCHITECTURE.md — Snowflake is serving-only, never a transform engine", BOUNDARY_MSG, ("boundary_contract.py",)),
    (".env.example", "flag dead AWS/NiFi vars; no new real ones without an ADR", BOUNDARY_MSG, ("boundary_contract.py",)),
    ("docs/ADR/", "ADR numbering + docs/DATA_MODEL.md cross-references", GRAIN_MSG, ("doc_reference_contract.py",)),
    ("docs/DATA_MODEL.md", "ADR-008 grain doctrine", GRAIN_MSG, ("doc_reference_contract.py",)),
]


def _rel(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except (ValueError, OSError):
        return path or ""


def _matches(rel: str) -> list[tuple[str, str, str, tuple[str, ...]]]:
    return [r for r in RULES if r[0] in rel]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    event = data.get("hook_event_name", "")
    rel = _rel((data.get("tool_input") or {}).get("file_path", ""))
    matches = _matches(rel)
    if not matches:
        return 0

    if event == "PreToolUse":
        lines = [f"⚠️ GOVERNED FILE: {rel} is under governance. Before editing, confirm against:"]
        for _, docs, msg, _ in matches:
            lines.append(f"  - {docs}: {msg}")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "\n".join(lines)}}))
        return 0

    if event == "PostToolUse":
        contracts: list[str] = []
        for _, _, _, scripts in matches:
            for s in scripts:
                if s not in contracts:
                    contracts.append(s)

        failures = []
        for script in contracts:
            proc = subprocess.run(
                [sys.executable, str(REPO / "tests" / script)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                failures.append(f"--- {script} ---\n{proc.stdout}{proc.stderr}")

        if failures:
            sys.stderr.write("Contract check FAILED after your edit — fix before continuing:\n" + "\n".join(failures))
            return 2  # feeds stderr back to Claude as a blocking error
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # never let a hook bug break the user's tool call
        raise SystemExit(0)
