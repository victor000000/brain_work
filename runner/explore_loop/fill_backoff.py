"""Backoff policy for consecutive submit failures in `fill_slots`.

Split out of `runner/explore_loop/fill.py`, which re-exports the constants. The
streak lives across passes in `state["submit_fail_streak"]`: a short one is
transient (brief backoff), a long one systemic (error-level alert + longer
backoff) so a settings/config error cannot spin silently forever.
"""

import time

from runner.explore_loop.constants import elog

# Consecutive failures across passes before the first backoff (transient).
TRANSIENT_FAIL_LIMIT = 4
TRANSIENT_BACKOFF_SEC = 60
# Consecutive failures treated as systemic (same error repeating).
SYSTEMIC_FAIL_LIMIT = 8
SYSTEMIC_BACKOFF_SEC = 600


def pause_if_needed(state, consecutive_fails):
    """Log and set the backoff when the fail streak crosses a threshold.

    Returns True when this pass must stop. Writing `submit_backoff_until` here
    rather than at the call site keeps both thresholds in one place.
    """
    if consecutive_fails >= SYSTEMIC_FAIL_LIMIT:
        elog.error(
            "B%d: %d consecutive submit failures — treating as systemic "
            "(settings/config or API outage); backing off %ds",
            state["batch_idx"],
            consecutive_fails,
            SYSTEMIC_BACKOFF_SEC,
        )
        state["submit_backoff_until"] = time.time() + SYSTEMIC_BACKOFF_SEC
        return True
    if consecutive_fails >= TRANSIENT_FAIL_LIMIT:
        elog.warning(
            "B%d: %d consecutive submit failures (transient); backing off %ds",
            state["batch_idx"],
            consecutive_fails,
            TRANSIENT_BACKOFF_SEC,
        )
        state["submit_backoff_until"] = time.time() + TRANSIENT_BACKOFF_SEC
        return True
    return False
