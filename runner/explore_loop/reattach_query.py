"""The orphan scan's SQL: find parent rows still worth re-attaching.

Split out of `runner/explore_loop/reattach_scan.py` (itself split from
`runner/explore_loop/reattach.py`), which re-exports `query_orphan_rows`.
"""

import time

from runner.explore_loop.constants import elog

# Stored timestamps are written by the submit path as text.
_TS_FORMAT = "%Y-%m-%d %H:%M:%S UTC"


def query_orphan_rows(conn, limit, max_age_sec, now):
    """SELECT the SUBMITTED parents that are still re-attachable.

    A parent qualifies when it is still SUBMITTED, has not stored a single-sim
    alpha, and was submitted inside the staleness window. Completed children
    do not exclude a multi-sim parent: a restart can interrupt child fetching
    or leave a child's alpha unstored. Polling is idempotent, and only the
    parent's terminal status proves its whole batch was handled.

    Most recent first, capped at `limit`. An unreadable scan yields no rows so
    the caller re-attaches nothing rather than dying at startup.
    """
    cutoff = time.strftime(_TS_FORMAT, time.gmtime(now - max_age_sec))
    try:
        return conn.execute(
            """
            SELECT s.sim_id, s.batch_idx, s.region, s.universe, s.delay,
                   s.expression, s.raw_settings, s.completed_at
              FROM simulations AS s
             WHERE s.status = 'SUBMITTED'
               AND s.parent_id IS NULL
               AND s.completed_at IS NOT NULL
               AND s.completed_at >= ?
               AND NOT EXISTS (
                     SELECT 1 FROM alpha_results AS a WHERE a.sim_id = s.sim_id
                   )
             ORDER BY s.rowid DESC
             LIMIT ?
            """,
            (cutoff, limit),
        ).fetchall()
    except Exception as e:
        elog.warning("Re-attach scan failed: %s", e)
        return []
