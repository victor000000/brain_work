"""Verify if alpha was actually submitted after 201 response."""

import logging
import time

from checker.auto_check_deferrals import _note_deferral
from core.log import get_file_logger
from runner.submit_progress import get_submission_progress
from runner.submit_retry import _increment_retry_count
from storage.store_submission_receipt import store_submission_receipt

API = "https://api.worldquantbrain.com"
log = logging.getLogger("brain")
clog = get_file_logger("check")

# After 201, dateSubmitted is set async. Poll briefly, but never block the
# maintenance thread for long: if the async confirmation has not landed within
# VERIFY_MAX_WAIT_SEC, return PENDING. The durable request journal ensures
# later passes reconcile with GET rather than repeating the submission POST.
VERIFY_MAX_WAIT_SEC = 15
VERIFY_POLL_INTERVAL_SEC = 5


def _get_alpha(session, alpha_id):
    """GET /alphas/{id}; return (status_code, dateSubmitted, status_field)."""
    resp = session.get(f"{API}/alphas/{alpha_id}", timeout=20)
    if resp.status_code != 200 or not resp.content:
        return resp.status_code, None, None
    data = resp.json()
    return 200, data.get("dateSubmitted"), data.get("status")


def _count_undecided(conn, alpha_id):
    """Count one undecided round and send the alpha to the back of the queue.

    Every path that leaves us not knowing whether the submission happened goes
    through here. The two transport-failure returns used to skip it: a GET that
    timed out or answered non-200 returned VERIFY_FAILED without counting the
    round and without deferring, so the alpha kept its sharpe rank, headed the
    next check run and was re-POSTed — and because VERIFY_FAILED is not in
    `checker.auto_check_alpha.UNDECIDED_OUTCOMES`, `_check_alpha` *deleted* the
    deferral row it should have left alone. That is the unbounded loop the
    count and the cooldown exist to bound, reachable whenever the platform is
    slow rather than when it is refusing: measured 2026-10-08, three alphas in
    ten minutes (`1YZdJpeJ`, `gJZ3AOAl`, `rKeW1wVo`) all returned VERIFY_FAILED
    on a read timeout.

    Bookkeeping must never be the thing that breaks a check, so it swallows.
    """
    try:
        _increment_retry_count(conn, alpha_id)
        _note_deferral(conn, alpha_id)
    except Exception as e:
        clog.warning("could not record the undecided round for %s: %s", alpha_id, e)


def verify_submission(session, conn, alpha_id):
    """After 201 from submit, check whether dateSubmitted is set.

    Bounded: total wait is capped at VERIFY_MAX_WAIT_SEC, then a clear PENDING
    outcome is returned instead of blocking the maintenance thread.
    """
    deadline = time.monotonic() + VERIFY_MAX_WAIT_SEC
    try:
        attempt = 0
        status = None
        progress_available = True
        while True:
            attempt += 1
            code, submitted, status = _get_alpha(session, alpha_id)
            clog.debug("Verify %s att=%d: HTTP %d submitted=%s", alpha_id, attempt, code, submitted)

            if code != 200:
                clog.warning("Verify %s: HTTP %d", alpha_id, code)
                _count_undecided(conn, alpha_id)
                return "VERIFY_FAILED"

            if submitted:
                store_submission_receipt(conn, alpha_id, submitted, status)
                clog.warning("SUBMITTED! %s status=%s date=%s", alpha_id, status, submitted)
                log.warning("ALPHA SUBMITTED: %s", alpha_id)
                return "SUBMITTED"

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                # An observation deadline does not establish the request outcome.
                # Preserve it for later GET reconciliation.
                _count_undecided(conn, alpha_id)
                clog.info(
                    "%s: 201 accepted, dateSubmitted not visible after %.0fs (status=%s) — PENDING, deferred",
                    alpha_id,
                    VERIFY_MAX_WAIT_SEC,
                    status,
                )
                return "PENDING"
            wait = VERIFY_POLL_INTERVAL_SEC
            if progress_available:
                progress = get_submission_progress(session, conn, alpha_id, timeout=min(20, remaining))
                if progress.outcome is not None:
                    return progress.outcome
                progress_available = not progress.unavailable
                if progress.retry_after is not None and progress.retry_after > 0:
                    wait = max(1.0, progress.retry_after)
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(wait, remaining))

    except Exception as e:
        clog.warning("Verify %s failed: %s", alpha_id, e)
        _count_undecided(conn, alpha_id)
        return "VERIFY_FAILED"
