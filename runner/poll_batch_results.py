"""Store a completed batch's results and mark its parent COMPLETE.

Split out of `runner/poll_batch.py`, which re-exports these names. The
`handle_single`/`handle_children` calls resolve at call time through
`runner.poll_batch`, which is the module tests patch them on.
"""

import time

from storage.store_sim import update_sim_status


def _poll_single(session, info, data, alpha_id, conn, settings, now, age):
    """Store the batch's single alpha; True once the parent row is COMPLETE."""
    from runner.poll_batch import handle_single, log, plog

    ok, err, complete = handle_single(session, info, data, conn, settings)
    if complete:
        update_sim_status(conn, info["pid"], "COMPLETE", error_msg=None, ts=now)
        plog.info("B%d done (single): %d ok, %d err alpha=%s age=%.0fs", info["idx"], ok, err, alpha_id, age)
        log.info("B%d done (single): %d ok, %d err age=%.0fs", info["idx"], ok, err, age)
        return True
    plog.warning("B%d single alpha %s not stored yet; will re-poll", info["idx"], alpha_id)
    return False


def _poll_multi(session, info, children, conn, settings, now, age):
    """Store the batch's children; True once every child is stored."""
    from runner.poll_batch import handle_children, log, plog

    ok, err, complete = handle_children(session, info, children, conn, settings, now)
    if complete:
        # A complete batch with no successful child is the platform failing, and
        # it IS what the incident breaker watches for — the earlier note here
        # said the opposite and cost the breaker its only input.
        #
        # The claim was that a complete batch can legitimately return ok=0
        # ("re-polls whose children are already stored count nothing into ok,
        # and unattributable extras count into err"). Tracing every return path
        # of `fetch_child` refutes it. A re-poll re-GETs each child and its
        # alpha, which returns (1, 0, True); when the child GET fails three
        # times and the child was already processed it returns (0, 0, True), so
        # err stays 0; a failed alpha fetch returns fetched=False and the batch
        # is not complete at all; and a child GET that fails without the child
        # being stored also returns fetched=False. The single path to
        # complete=True with err=1 is `poll_children_fetch.py`'s final return —
        # the platform answered HTTP 200 with a status outside
        # COMPLETE/WARNING, which is a failed simulation and nothing else.
        # `complete` requires every child, so ok=0 with err>0 means every child
        # failed. Measured 2026-10-10: 2,859 parent batches have all ten
        # children FAIL, `done: 0 ok, 10 err` lines ran 82/76/136/240 per day
        # on 10-06..10-09, and the breaker fired zero times across them because
        # `failed` was never set — so the streaks reset instead of advancing.
        if err and not ok:
            info["failed"] = True
        update_sim_status(conn, info["pid"], "COMPLETE", error_msg=None, ts=now)
        plog.info(
            "B%d done: %d ok, %d err (%d children) age=%.0fs %s/%s",
            info["idx"],
            ok,
            err,
            len(children),
            age,
            settings["region"],
            settings["universe"],
        )
        log.info("B%d done: %d ok, %d err age=%.0fs", info["idx"], ok, err, age)
        return True
    # Children came back this pass but not all of them: that is forward motion,
    # and `drop_stale` judges liveness by `last_advance_at` alone. One
    # `handle_children` pass can outlast `STALL_GRACE_SEC` by itself — a child
    # that needs all three `FETCH_RETRIES` costs ~66s — and the parent's own
    # `progress` stopped moving when it finished, so without this a batch that
    # is actively delivering results reads as frozen and is aborted with its
    # simulations already done and already paid for. Measured 2026-10-08/09:
    # B680 was dropped with "last progress 1184s ago" while the poll before it
    # had 7/10 of its children in hand; B682 (9/10) and B226 (9/10) the same.
    # The phase holds no BRAIN slot, so dropping it frees nothing.
    if ok:
        info["last_advance_at"] = time.time()
    plog.warning("B%d incomplete: %d/%d children fetched; will re-poll", info["idx"], ok, len(children))
    return False
