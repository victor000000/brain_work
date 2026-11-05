"""Keep the live allocator's targets aligned with the current Genius quarter."""

import time

from core.db import DBError
from core.log import get_file_logger
from tools.refresh_pyramid_targets.fetch import fetch_pyramid_alphas, fetch_pyramid_multipliers
from tools.refresh_pyramid_targets.persist import upsert_on_connection
from tools.refresh_pyramid_targets.quarter import quarter_bounds
from tools.refresh_pyramid_targets.score import compute_targets

log = get_file_logger("pyramid")


def refresh_quarter_targets(session, conn, max_age_seconds=21600):
    """Refresh dated targets via the sole writer; never open another connection.

    A recent all-time or previous-quarter snapshot is still invalid for Genius.
    Preserve it in the existing history table; never treat missing API data as
    a zero-count snapshot. Transport/storage failures propagate to the caller's
    existing startup/maintenance guards.
    """
    start, end = quarter_bounds()
    now = int(time.time())
    try:
        latest = conn.execute(
            "SELECT MIN(refreshed_at) FROM pyramid_targets WHERE period_start=? AND period_end=?",
            (start, end),
        ).fetchone()[0]
    except DBError:
        latest = None
    if latest is not None and 0 <= now - latest < max_age_seconds:
        return False
    counts = fetch_pyramid_alphas(session, start, end)
    multipliers = fetch_pyramid_multipliers(session)
    if not counts or not multipliers:
        log.warning("Quarterly targets not refreshed: incomplete API data for %s..%s", start, end)
        return False
    rows = compute_targets(counts, multipliers, start, end, now)
    if not rows:
        return False
    upsert_on_connection(conn, rows)
    log.info("Quarterly allocator targets refreshed: %s..%s, %d rows", start, end, len(rows))
    return True
