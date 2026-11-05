"""Refresh the pyramid snapshot if older than max_age_seconds (default 6h)."""

import time

# Late-bound lookup: tests monkeypatch `download.pyramid.fetch_pyramid_state`,
# so we resolve through the package namespace at call time rather than
# importing the function directly. The package re-exports it via __init__.py,
# which has already finished `from download.pyramid.fetch import …` by the
# time this module is loaded.
import download.pyramid as _pkg
from download.pyramid.fetch import plog
from download.pyramid.store import store_pyramid_state


def _latest_snapshot_ts(conn):
    """Return min(latest fetched_at across multipliers, alpha_counts) or None."""
    m_max = conn.execute("SELECT MAX(fetched_at) FROM pyramid_multipliers").fetchone()[0]
    a_max = conn.execute("SELECT MAX(fetched_at) FROM pyramid_alpha_counts").fetchone()[0]
    if m_max is None or a_max is None:
        return None
    return min(m_max, a_max)


def refresh_if_stale(session, conn, max_age_seconds=21600):
    """Refresh pyramid state iff the latest snapshot is at least max_age_seconds old.

    Staleness = now - MIN(MAX(fetched_at) over multipliers, MAX over counts).
    Empty tables are treated as infinitely stale.

    Returns True only if a refresh actually wrote a new snapshot. False when:
      - latest snapshot is fresh enough, or
      - a refresh was attempted but fetch_pyramid_state returned (None, None).

    Raises (does NOT swallow) if store_pyramid_state fails — e.g., a clock-
    collision PK violation or a DB-level error. Such failures are fail-loud.
    """
    now = int(time.time())
    latest = _latest_snapshot_ts(conn)
    if latest is not None and (now - latest) < max_age_seconds:
        return False

    multipliers, alpha_counts = _pkg.fetch_pyramid_state(session)
    if multipliers is None or alpha_counts is None:
        return False

    store_pyramid_state(conn, multipliers, alpha_counts, fetched_at=now)
    plog.info(
        "pyramid state refreshed: %d multipliers, %d counts at t=%d",
        len(multipliers),
        len(alpha_counts),
        now,
    )
    return True
