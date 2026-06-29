#!/usr/bin/env python3
"""Doc-reference contract — deterministic gate against documentation drift.

Ported from creative_intelligence_lab's tests/doc_reference_contract.py (pipeline-retrofit
effort). This repo has no dbt, so unlike home-credit/olist/paysim's contract there is no
MODEL-token check — only PATH refs (backtick-wrapped paths and []() link targets pointing at
a repo path) are checked.

Note on stale docs: docs/BRD.md, docs/DRD.md, docs/DQD.md, docs/PIPELINE_SPEC.md reference
paths from the abandoned NiFi/Glue design (e.g. `s3://volve-landing/`, `data_quality/suites/
bronze_production_suite.py`) that legitimately don't exist as real repo paths — those are
S3 URIs (not repo paths, not checked here) or already covered by the ALLOW list below with a
reason. This contract checks PATH DRIFT going forward, it does not retroactively fix the
staleness — that's a documentation-sherpa/business-analyst task tracked in INTERVIEW_GUIDE.md.

Stdlib only ($0, no deps). Exit 0 = every checked reference resolves. Exit 1 = drift.

What it checks:
  C1  PATH refs — backtick tokens and []() link targets that point at a repo path
      (bronze/ silver/ gold/ ml/ docs/ tests/ airflow/ .claude/ snowflake/ scripts/
      architecture/ learning/ simulation/ confluence/ ingestion/) must exist on disk.

Run:  python tests/doc_reference_contract.py
      python tests/doc_reference_contract.py path/to/FILE.md ...
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PATH_ROOTS = ("bronze/", "silver/", "gold/", "ml/", "docs/", "tests/", "airflow/", ".claude/",
              "snowflake/", "scripts/", "architecture/", "learning/", "simulation/",
              "confluence/", "ingestion/")

# Intentionally-not-yet-existing names a stale doc may legitimately reference. Each entry MUST
# carry a reason so the allowlist can't quietly rot into a dumping ground.
ALLOW: dict[str, str] = {
    "data_quality/suites/bronze_production_suite.py": "docs/DQD.md v1.0 (stale) — described GE suite never built, flagged in CLAUDE.md/INTERVIEW_GUIDE.md",
    "data_quality/suites/silver_production_suite.py": "docs/DQD.md v1.0 (stale) — described GE suite never built, flagged in CLAUDE.md/INTERVIEW_GUIDE.md",
    "data_quality/suites/silver_witsml_suite.py": "docs/DQD.md v1.0 (stale) — described GE suite never built, flagged in CLAUDE.md/INTERVIEW_GUIDE.md",
    "data_quality/suites/gold_feature_suite.py": "docs/DQD.md v1.0 (stale) — described GE suite never built, flagged in CLAUDE.md/INTERVIEW_GUIDE.md",
    "bronze/glue_jobs/bronze_production_daily.py": "docs/PIPELINE_SPEC.md v1.0 (stale) — abandoned Glue design, orphaned stub dir",
    "bronze/glue_jobs/bronze_drilling_witsml.py": "docs/PIPELINE_SPEC.md v1.0 (stale) — abandoned Glue design, orphaned stub dir",
    "bronze/glue_jobs/bronze_wellogs_las.py": "docs/PIPELINE_SPEC.md v1.0 (stale) — abandoned Glue design, never built (LAS source out of real scope)",
    "ingestion/nifi/templates/volve_router.xml": "ingestion/nifi/HOW_IT_WORKS.txt (stale stub) — NiFi template never built",
    "ingestion/nifi/scripts/route_witsml.groovy": "ingestion/nifi/HOW_IT_WORKS.txt (stale stub) — NiFi script never built",
}


def _default_docs() -> list[Path]:
    docs = [p for p in sorted((REPO / "docs").glob("*.md"))]
    adr = sorted((REPO / "docs" / "ADR").glob("*.md")) if (REPO / "docs" / "ADR").exists() else []
    root = [p for p in (REPO / "README.md", REPO / "CLAUDE.md") if p.exists()]
    return root + docs + adr


def check(docs: list[Path]) -> list[str]:
    errors: list[str] = []

    backtick = re.compile(r"`([^`]+)`")
    link = re.compile(r"\]\(([^)]+)\)")

    for doc in docs:
        if not doc.exists():
            errors.append(f"{doc}: doc file does not exist")
            continue
        text = doc.read_text(errors="ignore")
        rel_doc = doc.relative_to(REPO)

        candidates: list[str] = [m.group(1) for m in backtick.finditer(text)]
        candidates += [m.group(1) for m in link.finditer(text)]

        for token in candidates:
            token = token.strip()
            if not token.startswith(PATH_ROOTS):
                continue
            if token.endswith("/"):
                continue  # directory references not checked (existence of subtree varies)
            if "*" in token:
                continue  # glob reference (e.g. "gold/*.py") — not a single-file check
            path_part = token.split(":", 1)[0] if re.match(r"^.+\.\w+:\d", token) else token
            target = REPO / path_part
            if target.exists():
                continue
            if token in ALLOW or path_part in ALLOW:
                continue
            errors.append(f"{rel_doc}: references missing path '{token}' (not in ALLOW list)")

    return errors


def main() -> int:
    docs = [Path(a).resolve() for a in sys.argv[1:]] if len(sys.argv) > 1 else _default_docs()
    errors = check(docs)
    if errors:
        print(f"\n❌ DOC-REFERENCE CONTRACT FAILED — {len(errors)} violation(s):", file=sys.stderr)
        for e in sorted(set(errors)):
            print(f"   • {e}", file=sys.stderr)
        print("\n   Either fix the path or add to ALLOW with a reason. Fix before proceeding.", file=sys.stderr)
        return 1
    print(f"✅ doc-reference contract OK ({len(docs)} docs checked, no path drift)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
