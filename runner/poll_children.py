"""Handle multi-sim children results -- fetch each child and store."""

import logging
import time

from core.log import get_file_logger
from runner.poll_children_fetch import fetch_child
from storage.store_sim import update_sim_status

log = logging.getLogger("brain")
plog = get_file_logger("poll")


def _mark_mismatch(conn, info, message):
    """Flag the batch row with an error so it is not re-attached as healthy."""
    try:
        update_sim_status(conn, info["pid"], "SUBMITTED", error_msg=message)
    except Exception as e:
        plog.warning("B%d: could not record mismatch: %s", info["idx"], e)


def handle_children(session, info, children, conn, settings, now):
    """Iterate multi-sim children, fetch alpha for each, store results.

    Returns (ok, err, complete). `complete` is False when a child could not be
    fetched (batch stays in flight for a later retry) or when the children
    list length disagrees with the submitted expressions (only unambiguous
    pairs are stored; nothing is mis-attributed).
    """
    exprs = info.get("exprs") or []
    ok_count = 0
    err_count = 0
    complete = True

    if len(children) != len(exprs):
        message = f"children/exprs mismatch: {len(children)} children vs {len(exprs)} exprs"
        plog.error("B%d: %s", info["idx"], message)
        log.error("B%d: %s", info["idx"], message)
        _mark_mismatch(conn, info, message)
        if len(children) < len(exprs):
            # Cannot tell which expressions the returned children belong to;
            # store nothing rather than corrupt the attribution.
            return 0, len(children), False
        # More children than expressions: the first len(exprs) follow the
        # submission order, extras are unattributable and skipped.
        pairs = list(zip(children[: len(exprs)], exprs, strict=False))
        err_count += len(children) - len(exprs)
    else:
        pairs = list(zip(children, exprs, strict=True))

    for i, (child_id, expr) in enumerate(pairs):
        time.sleep(0.1)
        ok, err, fetched = fetch_child(session, info, child_id, i, len(children), expr, conn, settings, now)
        ok_count += ok
        err_count += err
        if not fetched:
            complete = False

    return ok_count, err_count, complete
