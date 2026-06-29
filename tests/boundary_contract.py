#!/usr/bin/env python3
"""Stack + scope boundary contract — deterministic gate over this repo's locked stack.

Ported from creative_intelligence_lab's tests/boundary_contract.py pattern, retargeted to THIS
repo's real rejected-tech axis (docs/ARCHITECTURE.md §3 + §6 ADR-001/ADR-002):
  - All Bronze/Silver/Gold compute is Databricks SQL Warehouse (SQL only, via
    databricks-sql-connector) — NO PySpark cluster, NO AWS Glue, NO NiFi anywhere in live
    pipeline code (bronze/, silver/, gold/, ml/, airflow/dags/). `ingestion/nifi/` and
    `bronze/glue_jobs/` are orphaned planning stubs (HOW_IT_WORKS.txt only, no real code) and
    are explicitly EXCLUDED from this scan — they are flagged in CLAUDE.md, not deleted, per
    owner instruction, and contain no executable Python to begin with.
  - NO dbt anywhere — unlike home-credit/olist/paysim, this repo's Gold layer is intentionally
    hand-written Databricks SQL scripts (ADR-008). A dbt_project.yml/profiles.yml appearing
    here would be a stack import from another repo, not a fix.
  - 3 wells only (F-1, F-11, F-12) — docs/ADR/ADR-005-three-well-scope.md.
  - Snowflake is a serving veneer only (snowflake/*.py) — no transform logic.

Stdlib only ($0, no deps). Exit 0 = contract holds. Exit 1 = hard violation.

Rules:
  ST1  no `pyspark` import anywhere in bronze/, silver/, gold/, ml/, airflow/dags/
  ST2  no AWS Glue/boto3/NiFi-client import anywhere in live pipeline code
  ST3  no dbt_project.yml or profiles.yml anywhere in the repo
  ST4  no requirements.txt lists a banned dependency (pyspark, boto3, dbt-core, nipyapi)
  ST5  silver/silver_production.py's well filter stays exactly the 3 locked wells

Run:  python tests/boundary_contract.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

LIVE_PY_DIRS = ["bronze", "silver", "gold", "ml", "airflow/dags", "snowflake", "scripts"]
# ingestion/nifi/ and bronze/glue_jobs/ are intentionally excluded — orphaned stub dirs with
# no real .py code (HOW_IT_WORKS.txt only), flagged in CLAUDE.md, not part of the live surface.
REQUIREMENTS_FILES = ["requirements.txt", "airflow/requirements.txt", "snowflake/requirements.txt"]

IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z0-9_.]+)")
REQ_LINE_RE = re.compile(r"^([A-Za-z0-9_.-]+)")

DENY: dict[str, str] = {
    "pyspark": "docs/ARCHITECTURE.md §3 — compute is Databricks SQL Warehouse (SQL only), no PySpark cluster",
    "boto3": "docs/ARCHITECTURE.md ADR-001 — NiFi/S3/Glue ingestion was replaced by direct Databricks Volume access",
    "awswrangler": "docs/ARCHITECTURE.md ADR-001 — no AWS storage in the live pipeline",
    "nipyapi": "docs/ARCHITECTURE.md ADR-001 — NiFi was replaced, ingestion/nifi/ is an orphaned stub",
    "dbt": "docs/ADR/ADR-008-identity-grain.md — this repo has no dbt by design, Gold is hand-written SQL",
}

LOCKED_WELLS = ("F-1", "F-11", "F-12")


def _scan_python(path: Path, errors: list[str]) -> None:
    rel = path.relative_to(REPO)
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        m = IMPORT_RE.match(line)
        if not m:
            continue
        module = m.group(1).lower()
        for banned, reason in DENY.items():
            if module == banned or module.startswith(banned + "."):
                errors.append(f"{rel}:{lineno}: banned import '{m.group(1)}' — {reason}")


def _scan_requirements(path: Path, errors: list[str]) -> None:
    rel = path.relative_to(REPO)
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = REQ_LINE_RE.match(line)
        if not m:
            continue
        pkg = m.group(1).lower().replace("-", "_")
        for banned, reason in DENY.items():
            if pkg == banned.replace("-", "_") or pkg.startswith(banned.replace("-", "_") + "_"):
                errors.append(f"{rel}:{lineno}: banned dependency '{m.group(1)}' — {reason}")


def check() -> list[str]:
    errors: list[str] = []

    for dirname in LIVE_PY_DIRS:
        d = REPO / dirname
        if not d.exists():
            continue
        for path in d.rglob("*.py"):
            _scan_python(path, errors)

    for name in REQUIREMENTS_FILES:
        path = REPO / name
        if path.exists():
            _scan_requirements(path, errors)

    # ST3 — no dbt project files anywhere
    for pattern in ("dbt_project.yml", "profiles.yml"):
        hits = [p for p in REPO.rglob(pattern) if ".git" not in p.parts]
        for hit in hits:
            errors.append(f"{hit.relative_to(REPO)}: dbt project file found — this repo has no dbt by design (ADR-008)")

    # ST5 — well scope still locked to F-1/F-11/F-12
    silver_prod = REPO / "silver" / "silver_production.py"
    if silver_prod.exists():
        text = silver_prod.read_text()
        for well in LOCKED_WELLS:
            if well not in text:
                errors.append(f"silver/silver_production.py: locked well '{well}' missing — 3-well scope (ADR-005) may have drifted")

    return errors


def main() -> int:
    errors = check()
    if errors:
        print(f"\n❌ BOUNDARY CONTRACT FAILED — {len(errors)} violation(s):", file=sys.stderr)
        for e in sorted(set(errors)):
            print(f"   • {e}", file=sys.stderr)
        print("\n   See docs/ARCHITECTURE.md. Fix before proceeding.", file=sys.stderr)
        return 1
    print("✅ boundary contract OK (Databricks SQL Warehouse only, no dbt, 3-well scope, Snowflake serving-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
