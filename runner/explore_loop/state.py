"""The run state an explore-loop pass mutates: initial values + crash recovery.

Split out of `runner/explore_loop/loop.py`, which re-exports both names. The
comments here are the field-level "why" (measured reset behaviour, restart
incidents) and travel with the keys they explain.
"""

from runner.explore_loop.constants import elog
from runner.explore_loop.reattach import reattach_orphans


def _initial_state():
    return {
        "inflight": [],
        "batch_idx": 0,
        "done_count": 0,
        "budget_exhausted": False,
        "concurrent": False,
        # Last done_count value at which periodic_maintenance ran.
        # Gating on (done >= last_check_done + CHECK_INTERVAL) instead of
        # (done % CHECK_INTERVAL == 0) avoids re-firing every loop iteration
        # while done_count sits unchanged at a multiple-of-50 boundary.
        "last_check_done": 0,
        # Last done_count at which the submission check ran. Separate from
        # `last_check_done` because it fires far more often (see
        # CHECK_INTERVAL_SUBMIT) — a gate-passing alpha should not wait on the
        # heavy priors/pyramid refreshes to be looked at.
        "last_submit_check_done": 0,
        "last_submit_check_ts": 0.0,
        # Consecutive CONCURRENT submit attempts; drives escalating backoff.
        "concurrent_streak": 0,
        # Cross-pass submit failure streak; a systemic settings/config error
        # keeps growing instead of resetting every pass.
        "submit_fail_streak": 0,
        # Simulation-error incident breaker (see explore_loop/error_breaker).
        "sim_error_streak": 0,
        "error_backoff_count": 0,
        "sim_error_pause_until": 0.0,
        # Poll pacing state (see explore_loop.poll).
        "last_poll_ts": 0.0,
        "poll_backoff_until": 0.0,
        "poll_throttled": False,
    }


def recover_reattached(state, conn) -> None:
    """Re-attach batches accepted before a crash/restart.

    They are still running (and holding slots) on BRAIN, but the in-memory
    inflight list is gone. Not capped at `max_concurrent`: these are already
    running and already paid for. `fill_slots` holds off submitting while the
    list is long.
    """
    try:
        state["inflight"] = reattach_orphans(conn)
        if state["inflight"]:
            state["batch_idx"] = max((b.get("idx") or 0) for b in state["inflight"]) + 1
    except Exception as e:
        elog.error("Startup re-attach failed (continuing with empty state): %s", e, exc_info=True)
        state["inflight"] = []
