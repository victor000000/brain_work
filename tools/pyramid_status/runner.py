"""Top-level orchestration for `python3 -m tools.pyramid_status`."""

import argparse
import time

# Imported here so the package's ad-hoc sys.path injection in _config runs first.
from core.auth import get_session
from tools.pyramid_status._config import ACTIVE_THRESHOLD, DEFAULT_STATUSES
from tools.pyramid_status._log import log
from tools.pyramid_status.attribution import build_attributions
from tools.pyramid_status.fetch import fetch_alphas_by_status, fetch_pyramid_multipliers
from tools.pyramid_status.persist import dump_json, persist_to_db
from tools.pyramid_status.report import (
    report_alphas_per_pyramid,
    report_top_multipliers,
    report_uncovered_active,
)


def _fetch_alphas_per_status(session, statuses):
    """Pull alphas for each requested status, swallowing per-status errors."""
    alphas_by_status = {}
    for st in statuses:
        try:
            xs = fetch_alphas_by_status(session, st)
        except Exception as e:
            log.warning("Failed to fetch status=%s: %s", st, e)
            continue
        if xs:
            alphas_by_status[st] = xs
            log.info("status=%-15s alphas=%d", st, len(xs))
    return alphas_by_status


def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--statuses", default=",".join(DEFAULT_STATUSES))
    ap.add_argument(
        "--no-detail", action="store_true", help="Skip per-alpha /alphas/{id} fetch (no pyramid attribution)."
    )
    return ap.parse_args()


def main():
    args = _parse_args()
    statuses = [s.strip() for s in args.statuses.split(",") if s.strip()]
    fetched_at = int(time.time())

    log.info("=" * 60)
    log.info("BRAIN pyramid status snapshot")
    log.info("=" * 60)

    session = get_session()

    multipliers = fetch_pyramid_multipliers(session)
    log.info("Pyramid multipliers: %d entries", len(multipliers))
    boosted = [m for m in multipliers if m.get("multiplier", 0) > ACTIVE_THRESHOLD]
    log.info("Active (multiplier > %.1f): %d", ACTIVE_THRESHOLD, len(boosted))

    alphas_by_status = _fetch_alphas_per_status(session, statuses)

    if args.no_detail:
        attributions, pyramid_to_alphas = [], {}
    else:
        attributions, pyramid_to_alphas = build_attributions(session, alphas_by_status)

    persist_to_db(multipliers, attributions, fetched_at)
    dump_json(multipliers, alphas_by_status, attributions, fetched_at)

    report_top_multipliers(multipliers)
    report_alphas_per_pyramid(pyramid_to_alphas, attributions)
    report_uncovered_active(multipliers, pyramid_to_alphas)
