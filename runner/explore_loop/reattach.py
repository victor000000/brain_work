"""Re-attach parent simulations orphaned by a crash or restart.

The explore loop keeps in-flight batches only in memory. When the process dies
(crash, restart, laptop sleep), those 201-accepted batches keep running — and
holding concurrent slots — on BRAIN while the local state forgets them. On
startup we rescan `simulations` for parent rows still marked SUBMITTED and
re-attach them to the poll loop, including batches with some children stored.

The scan itself (query + row decoding) lives in `reattach_scan`; this module is
the startup entry point and re-exports the scan pieces it was split from.
"""

import time

from runner.explore_loop.constants import elog
from runner.explore_loop.reattach_scan import (  # noqa: F401
    API_BASE,
    _decode_exprs,
    _decode_settings,
    _epoch,
    build_batches,
    query_orphan_rows,
)

# Only consider parents submitted within this window; anything older is a
# long-dead orphan and must not be re-polled forever.
REATTACH_MAX_AGE_SEC = 6 * 3600

# How many orphans one startup will re-attach. Deliberately NOT `max_concurrent`:
# that is a *submission* budget, and an orphan is work already running and
# already paid for. Tying the two stranded simulations — the scan caps its
# result, the caller assigned the capped list to `inflight`, and the batches
# past the cap kept running on BRAIN with nothing polling them, so their alphas
# were never fetched. Observed 2026-10-06: three restarts in six minutes each
# returned exactly the cap (8, 8, 4), and the platform then cancelled whole
# batches as the untracked ones plus the freshly submitted ones overran the
# account's concurrent-simulation limit. `fill_slots` already stops submitting
# while `inflight` is at or above `max_concurrent`, so a long list drains
# rather than piling more on.
REATTACH_MAX_BATCHES = 64


def find_orphan_batches(conn, limit, max_age_sec=REATTACH_MAX_AGE_SEC, now=None):
    """Return re-attachable batch dicts for orphaned parent simulations.

    A parent qualifies when it is still SUBMITTED, has not stored a single-sim
    alpha, and was submitted inside the staleness window. Partially fetched
    multi-sim batches remain recoverable. Most recent first, capped at `limit`.
    """
    now = time.time() if now is None else now
    return build_batches(query_orphan_rows(conn, limit, max_age_sec, now), now)


def reattach_orphans(conn, limit=REATTACH_MAX_BATCHES, max_age_sec=REATTACH_MAX_AGE_SEC, now=None):
    """Find + log orphaned batches for startup re-attachment."""
    batches = find_orphan_batches(conn, limit, max_age_sec=max_age_sec, now=now)
    if len(batches) >= limit:
        # Never silent again: at the cap, the batches that did not fit are
        # running untracked and their results are lost.
        elog.warning(
            "Re-attach hit its cap of %d — any further running orphan is untracked and its alphas will be lost",
            limit,
        )
    for batch in batches:
        elog.warning(
            "RE-ATTACH B%s parent=%s age=%.0fs (%s/%s)",
            batch["idx"],
            batch["pid"],
            (time.time() if now is None else now) - batch["submitted_at"],
            batch["settings"]["region"],
            batch["settings"]["universe"],
        )
    if batches:
        elog.warning("Re-attached %d orphaned batch(es) from a previous run", len(batches))
    return batches
