"""Poll accepted batches and report slow jobs without automatic cancellation.

Slow-job reporting lives in `runner.explore_loop.poll_stale`, explicit
server-side cancellation in `runner.explore_loop.poll_abort` and the final fetch of a
finished-but-unreadable batch in `runner.explore_loop.poll_final`; all are
re-exported here so `from runner.explore_loop.poll import ...` keeps working
for callers and tests.
"""

import time

from runner.explore_loop.constants import elog
from runner.explore_loop.error_breaker import note_batch_done
from runner.explore_loop.poll_abort import (  # noqa: F401
    MAX_FINAL_FETCHES,
    _abort_server_side,
    _refused_as_complete,
)
from runner.explore_loop.poll_final import _fetch_finished  # noqa: F401
from runner.explore_loop.poll_stale import drop_stale  # noqa: F401
from runner.poll_batch import poll_batch

# Minimum wall-clock gap between poll rounds. With max_concurrent batches this
# caps us at roughly max_concurrent/MIN_POLL_INTERVAL GETs per second, well
# inside the account's sim budget.
MIN_POLL_INTERVAL_SEC = 25

# Never park the poll loop longer than this because of one Retry-After value.
MAX_POLL_BACKOFF_SEC = 300


def poll_inflight(session, state, conn):
    """Poll all inflight batches; return how many freed this pass.

    One batch raising can never abort the round: the batch is logged and kept
    in flight. Pacing (minimum interval + Retry-After backoff) is applied here
    so the poll traffic stays within the account budget.
    """
    now = time.time()
    earliest = max(
        state.get("last_poll_ts", 0.0) + MIN_POLL_INTERVAL_SEC,
        state.get("poll_backoff_until", 0.0),
    )
    if now < earliest:
        return 0
    state["last_poll_ts"] = now

    still_pending = []
    freed = 0
    throttle_seen = False
    for batch in state["inflight"]:
        try:
            done = poll_batch(session, batch, conn)
        except Exception as e:
            # %s, not %d: this handler exists so that "one batch raising can
            # never abort the round", and a `%d` fed a `.get()` with no default
            # would raise a second time — inside the handler — on exactly the
            # malformed batch it is here to survive.
            elog.error("B%s poll raised, keeping batch in flight: %s", batch.get("idx"), e, exc_info=True)
            done = False
        if done:
            state["done_count"] += 1
            freed += 1
            # Feed the incident breaker: a done batch with no results is the
            # platform failing, not us — a streak of them pauses new submits.
            note_batch_done(state, bool(batch.get("failed")))
            elog.debug("B%d completed (done=%d)", batch["idx"], state["done_count"])
        else:
            if batch.get("poll_throttled"):
                throttle_seen = True
            still_pending.append(batch)
    state["inflight"] = still_pending
    state["poll_throttled"] = throttle_seen

    retries = [b.get("retry_after") for b in still_pending if b.get("retry_after")]
    if retries:
        delay = min(max(retries), MAX_POLL_BACKOFF_SEC)
        state["poll_backoff_until"] = max(state.get("poll_backoff_until", 0.0), time.time() + delay)
    return freed
