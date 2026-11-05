"""Top-level runner for `python3 -m tools.refresh_pyramid_targets`."""

import argparse
import time

# Imported here so the package's _config sys.path injection runs first.
from core.auth import get_session
from tools.refresh_pyramid_targets._log import log
from tools.refresh_pyramid_targets.fetch import fetch_pyramid_alphas, fetch_pyramid_multipliers
from tools.refresh_pyramid_targets.persist import upsert
from tools.refresh_pyramid_targets.quarter import quarter_bounds
from tools.refresh_pyramid_targets.report import report_distribution, report_top_priority
from tools.refresh_pyramid_targets.score import compute_targets


def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--period",
        choices=["current", "all"],
        default="current",
        help="current = current calendar quarter (default); all = no date filter",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="write the snapshot; without it this is a dry run",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="explicit no-write mode (the default; wins over --apply)",
    )
    return ap.parse_args()


def main():
    args = _parse_args()
    if args.period == "all":
        start, end = "", ""
    else:
        start, end = quarter_bounds()

    log.info("=" * 60)
    log.info("Refreshing pyramid_targets [period=%s start=%s end=%s]", args.period, start, end)
    log.info("=" * 60)

    session = get_session()
    alphas = fetch_pyramid_alphas(session, start, end)
    mults = fetch_pyramid_multipliers(session)
    log.info("Fetched: %d pyramid-alpha rows, %d multiplier rows", len(alphas), len(mults))

    refreshed_at = int(time.time())
    rows = compute_targets(alphas, mults, start or None, end or None, refreshed_at)
    log.info("Computed %d target rows", len(rows))

    report_distribution(rows)
    report_top_priority(rows)

    if args.dry_run and args.apply:
        log.warning("both --apply and --dry-run given — dry-run wins, nothing written")
    if not args.apply or args.dry_run:
        log.info("dry run — nothing written; re-run with --apply to store the snapshot")
        return

    result = upsert(rows)
    log.info(
        "Stored snapshot: %d history rows, %d current rows (%d archived)",
        result["history"],
        result["current"],
        result["archived"],
    )
