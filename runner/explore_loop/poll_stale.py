"""Report slow accepted jobs without cancelling them on an observation clock."""

import time

from runner.explore_loop.constants import STALE_HARD_TIMEOUT, STALE_TIMEOUT, STALL_GRACE_SEC, elog


def drop_stale(session, state, conn=None):
    """Retain accepted handles until ordinary polling reconciles native outcomes.

    The legacy function name remains for callers. Neither elapsed age nor a
    stationary progress percentage proves failure. In particular, a job still
    returning 35% must not be DELETEd to make room for speculative new work.
    Explicit cancellation remains separate from automatic observation.
    """
    if state.get("poll_throttled"):
        return
    now = time.time()
    for batch in state["inflight"]:
        age = now - batch.get("submitted_at", now)
        last_advance = batch.get("last_advance_at", batch.get("submitted_at", now))
        stalled = now - last_advance > STALL_GRACE_SEC
        if age > STALE_HARD_TIMEOUT or (age > STALE_TIMEOUT and stalled):
            if now < batch.get("slow_notice_after", 0):
                continue
            batch["slow_notice_after"] = now + STALL_GRACE_SEC
            elog.warning(
                "SLOW B%d retained after %.0fs (%s/%s, last progress %.0fs ago); awaiting native outcome",
                batch["idx"],
                age,
                batch["settings"]["region"],
                batch["settings"]["universe"],
                now - last_advance,
            )
