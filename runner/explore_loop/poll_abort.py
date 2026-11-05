"""Abort a stale batch server-side, or fetch it when the delete is refused.

Split out of `runner/explore_loop/poll.py`, which re-exports these names. The
DELETE endpoint is undocumented, so everything here is defensive: a refusal
because the simulation completed means the result is still fetchable.
"""

import time

from runner.explore_loop.constants import elog
from runner.explore_loop.poll_final import _fetch_finished
from runner.http_retry import retry_after_or
from storage.store_sim import update_sim_status

# Bound immediate final fetches, then back off without discarding the handle.
MAX_FINAL_FETCHES = 3
ABORT_RETRY_SEC = 60


def _refused_as_complete(resp) -> bool:
    """True when BRAIN refused the DELETE because the simulation had finished.

    The body is `["Can not delete complete simulations"]`. A finished
    simulation is exactly the case the drop must not throw away — the batch
    stopped reporting progress, but the budget has been spent and the result is
    sitting there to be fetched.
    """
    try:
        body = resp.json()
        text = " ".join(str(x) for x in body) if isinstance(body, list) else str(body)
    except Exception:
        text = resp.text or ""
    return "complete simulations" in text.lower()


def _fetch_complete(batch, session, conn):
    if _fetch_finished(session, batch, conn):
        return True
    tries = batch.get("final_fetches", 0) + 1
    batch["final_fetches"] = tries
    if tries >= MAX_FINAL_FETCHES:
        batch["abort_retry_at"] = time.time() + ABORT_RETRY_SEC
        batch["final_fetches"] = 0
    elog.warning("STALE B%d finished but unreadable — retaining handle (fetch %d)", batch["idx"], tries)
    return False


def _abort_server_side(session, batch, conn) -> bool:
    """Release only an acknowledged cancellation or a reconciled result.

    A refusal, transport error or fetch deadline cannot prove a terminal job.
    Retain its durable parent and reservation, with cancellation retry backoff
    while ordinary polling can still reconcile it.
    """
    if batch.get("abort_retry_at", 0) > time.time():
        return False
    if batch.get("server_complete"):
        return _fetch_complete(batch, session, conn)
    loc = batch.get("loc")
    cancelled = batch.get("server_cancelled", False)
    retry = float(ABORT_RETRY_SEC)
    if loc and not cancelled:
        resp = None
        try:
            resp = session.delete(loc, timeout=20)
            retry = max(retry, retry_after_or(resp.headers, ABORT_RETRY_SEC))
            if resp.status_code in (200, 204):
                cancelled = True
                batch["server_cancelled"] = True
                elog.info("STALE B%d aborted server-side: HTTP %d", batch["idx"], resp.status_code)
            elif _refused_as_complete(resp):
                batch["server_complete"] = True
                return _fetch_complete(batch, session, conn)
            else:
                elog.warning(
                    "STALE B%d abort: HTTP %d body=%s",
                    batch["idx"],
                    resp.status_code,
                    resp.text[:120] if resp.content else "",
                )
        except Exception as e:
            elog.warning("STALE B%d abort raised: %s", batch["idx"], e)
    if not cancelled:
        batch["abort_retry_at"] = time.time() + retry
        return False
    try:
        if conn is not None and batch.get("pid"):
            update_sim_status(conn, batch["pid"], "CANCELLED")
    except Exception as e:
        elog.warning("STALE B%d local abort mark failed: %s", batch["idx"], e)
        batch["abort_retry_at"] = time.time() + ABORT_RETRY_SEC
        return False
    return True
