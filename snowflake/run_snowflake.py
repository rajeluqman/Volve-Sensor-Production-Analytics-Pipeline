"""
Phase 8 — Snowflake Serving Layer
run_snowflake.py: Orchestrator — setup tables → load data → create views.

Usage:
  python run_snowflake.py              # full pipeline
  python run_snowflake.py --only setup
  python run_snowflake.py --only load
  python run_snowflake.py --only views
"""

import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Snowflake Serving Layer orchestrator")
    parser.add_argument(
        "--only",
        choices=["setup", "load", "views"],
        help="Run a single step instead of the full pipeline",
    )
    args = parser.parse_args()

    from setup_snowflake import setup
    from load_snowflake import load
    from create_views import create_views

    steps = {
        "setup": setup,
        "load":  load,
        "views": create_views,
    }

    if args.only:
        log.info("Running step: %s", args.only)
        steps[args.only]()
    else:
        log.info("=== Phase 8 — Snowflake Serving Layer: full pipeline ===")
        for name, fn in steps.items():
            log.info("--- Step: %s ---", name)
            fn()
        log.info("=== Phase 8 complete — VOLVE_DB.SERVING ready ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.error("Pipeline failed: %s", exc)
        sys.exit(1)
