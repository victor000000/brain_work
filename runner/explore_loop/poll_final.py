"""Fetch a batch the platform says is complete instead of dropping it.

Split out of `runner/explore_loop/poll.py`, which re-exports `_fetch_finished`.
"""

from runner.explore_loop.constants import elog


def _fetch_finished(session, batch, conn) -> bool:
    """Fetch a batch the platform says is complete. True when it resolved.

    One poll with the pacing keys cleared — `poll_batch` returns early on
    Retry-After, and a finished simulation has no reason to send one. A fetch
    that still fails retains the accepted handle for later reconciliation;
    the cancellation caller bounds immediate retries with backoff.
    """
    # Imported at call time so the name resolves through `runner.explore_loop.poll`,
    # which is where tests patch it.
    from runner.explore_loop.poll import poll_batch

    batch.pop("retry_after", None)
    batch.pop("poll_throttled", None)
    try:
        done = poll_batch(session, batch, conn)
    except Exception as e:
        elog.warning("STALE B%d final fetch raised: %s", batch["idx"], e)
        return False
    if done:
        elog.warning("STALE B%d was already finished — fetched instead of dropping it", batch["idx"])
    return done
