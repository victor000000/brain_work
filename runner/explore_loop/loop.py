"""Top-level run_explore_loop — generate / submit / poll cycle.

The run-state dict (initial values and restart recovery) lives in
`runner.explore_loop.state` and is re-exported here.
"""

import core.budget as budget
from runner.explore_helpers import periodic_maintenance
from runner.explore_loop.constants import STALE_TIMEOUT, elog
from runner.explore_loop.error_breaker import paused as error_paused
from runner.explore_loop.fill import fill_slots
from runner.explore_loop.poll import drop_stale, poll_inflight
from runner.explore_loop.sleep_logic import sleep_after_pass
from runner.explore_loop.startup import _startup_checks
from runner.explore_loop.state import _initial_state, recover_reattached


def run_explore_loop(session, conn, max_concurrent=6):
    """Tight loop: generate, submit, poll. Runs until budget exhausted (then sleeps and resumes).

    No single batch, response, or maintenance failure may abort the loop: each
    phase is guarded, and each batch is polled inside its own guard.
    """
    state = _initial_state()

    _startup_checks(session, conn)

    recover_reattached(state, conn)

    elog.info(
        "Explore loop started: max_concurrent=%d, stale_timeout=%ds, reattached=%d",
        max_concurrent,
        STALE_TIMEOUT,
        len(state["inflight"]),
    )

    while True:
        try:
            freed = poll_inflight(session, state, conn)
        except Exception as e:
            elog.error("poll_inflight failed, keeping state: %s", e, exc_info=True)
            freed = 0
        try:
            drop_stale(session, state, conn)
        except Exception as e:
            elog.error("drop_stale failed: %s", e, exc_info=True)
        if not state["budget_exhausted"] and not state["concurrent"] and not error_paused(state):
            try:
                fill_slots(session, state, conn, max_concurrent)
            except Exception as e:
                elog.error("fill_slots failed: %s", e, exc_info=True)
        try:
            periodic_maintenance(state, conn, session, freed)
        except Exception as e:
            elog.error("periodic_maintenance failed: %s", e, exc_info=True)

        if not state["budget_exhausted"] and budget.is_exhausted():
            state["budget_exhausted"] = True

        try:
            sleep_after_pass(state)
        except Exception as e:
            elog.error("sleep_after_pass failed: %s", e, exc_info=True)
