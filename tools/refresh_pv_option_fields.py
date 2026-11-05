#!/usr/bin/env python3
"""Refresh price (pv) and options (option) field data from BRAIN.

The full downloader (`download/brain_data.py`) walks every subcategory. This
walks only the five pv/option subcategories, across every (region, universe,
delay) in `download.fetch_fields.REGION_CONFIG`, and rewrites the field rows
via the usual INSERT OR REPLACE path.

`is_downloaded` would normally skip combos already in download_log, so this
first clears the pv/option entries — that is what makes it a refresh rather
than a no-op re-run.

By default this is a true refresh: it clears the pv/option download_log rows
so every combo is re-fetched. That makes a restart expensive — pass --resume to
keep the log and continue from where a previous run stopped.

Usage:
    python3 tools/refresh_pv_option_fields.py --dry-run
    python3 tools/refresh_pv_option_fields.py
    python3 tools/refresh_pv_option_fields.py --resume
"""

import argparse
import os
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.refresh_pv_option_env import (  # noqa: F401
    DB_PATH,
    PV_OPT_PREFIXES,
    count_combos,
    is_pv_option,
    log,
)
from tools.refresh_pv_option_setup import clear_download_log, open_and_select, refresh_and_report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report scope, touch nothing")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="keep download_log and continue a previous run instead of re-fetching everything",
    )
    args = ap.parse_args()

    combos = count_combos()
    log.info("=" * 60)
    log.info("pv/option field refresh — %d (region, universe, delay) combos", combos)
    log.info("=" * 60)

    brain, conn, pv_opt, stale = open_and_select()

    if args.dry_run:
        log.info("dry run — no changes made")
        for s in pv_opt:
            log.info("  would refresh %s (%s)", s["id"], s.get("name"))
        return

    if args.resume:
        log.info("--resume: keeping download_log, continuing from %d recorded combos", stale)
    else:
        clear_download_log(conn)
        log.info("cleared pv/option download_log — starting download")

    refresh_and_report(brain, conn, pv_opt)


if __name__ == "__main__":
    main()
