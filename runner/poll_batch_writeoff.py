"""Decide whether a finished-without-result body writes the batch off.

Split out of `runner/poll_batch.py`, which re-exports `_write_off_no_result`.
"""

import logging

from core.log import get_file_logger
from runner.poll_batch_errors import _ERROR_STATUSES, MIN_ERROR_AGE_SEC, _record_batch_error

plog = get_file_logger("poll")
log = logging.getLogger("brain")


def _write_off_no_result(conn, info, data, status, children, alpha_id, age, now) -> bool | None:
    """Write off a no-result body; True terminal, False re-poll, None other.

    None means the body carries a result (children or an alpha) and the caller
    should keep going down the normal completion path.
    """
    # A finished-without-result response: ERROR/FAIL body status, or an empty
    # body that has neither children nor an alpha. Observed 2026-10-03: the
    # platform returns exactly this for freshly submitted batches that are
    # still running — the children appear a minute or two later — so a batch
    # younger than MIN_ERROR_AGE_SEC is always re-polled. Only past that age,
    # and only when the condition repeats, is it written off.
    #
    # `not children` guards the ERROR status: the platform labels a multi-sim
    # parent ERROR while still listing its children, and those children are
    # fetched separately and carry the real result. Writing the batch off on
    # the parent's label alone discards simulations the budget has already
    # paid for — measured 2026-10-06, 13 of 25 written-off batches still had
    # their 10 children under the ERROR parent. Only a body with nothing left
    # to fetch is terminal.
    #
    # The guard is the negation of that condition: no children to fetch, and
    # either an ERROR/FAIL status or no alpha on the parent.
    if children or (status not in _ERROR_STATUSES and alpha_id):
        return None
    if age < MIN_ERROR_AGE_SEC:
        plog.debug(
            "B%d: no-result body (status=%s) age=%.0fs < %ds — re-polling",
            info["idx"],
            status or "NONE",
            age,
            MIN_ERROR_AGE_SEC,
        )
        return False
    strikes = info.get("error_strikes", 0) + 1
    info["error_strikes"] = strikes
    if strikes < 2:
        plog.warning(
            "B%d: no-result body (status=%s) strike %d — re-polling",
            info["idx"],
            status or "NONE",
            strikes,
        )
        return False
    msg = data.get("message") or data.get("detail") or f"simulation finished without result (status={status or 'NONE'})"
    _record_batch_error(conn, info, str(msg), now)
    plog.error("B%d done (error): %s age=%.0fs", info["idx"], str(msg)[:160], age)
    log.error("B%d error: %s", info["idx"], str(msg)[:120])
    # Marks the batch for the incident breaker (see explore_loop/error_breaker).
    info["failed"] = True
    return True
