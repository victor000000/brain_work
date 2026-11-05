"""Decide how long the explore loop should sleep between iterations."""

import time

import core.budget as budget
from runner.explore_helpers._constants import CHECK_MAX_IDLE_SEC
from runner.explore_loop.constants import elog

# Escalating backoff for repeated CONCURRENT 429s. The previous fixed 30s nap
# hammered BRAIN every half-minute when the account-wide concurrent quota was
# saturated (e.g. by stale-dropped sims still running server-side), wasting
# generation work each iteration. Cap at 10 minutes so we still recover when
# the saturation clears.
CONCURRENT_BASE = 30
CONCURRENT_MAX = 600


def _concurrent_backoff(streak):
    """30, 60, 120, 240, 480, 600, 600, ... (capped at CONCURRENT_MAX)."""
    if streak <= 1:
        return CONCURRENT_BASE
    return min(CONCURRENT_BASE * (2 ** (streak - 1)), CONCURRENT_MAX)


def sleep_after_pass(state):
    """Apply the post-iteration sleep based on current loop state.

    Cases:
      - Budget exhausted with no in-flight batches: sleep until the budget
        resets (capped at 1h, floored at 60s as a safety net).
      - Concurrent-limit pause with no in-flight: escalating backoff
        (30s → 60s → 120s → ... up to CONCURRENT_MAX).
      - Concurrent flag still set with in-flight: short 45s tap.
      - Otherwise: 5s when idle, 3s when work is in flight.
    """
    if state["budget_exhausted"] and not state["inflight"]:
        wait = budget.seconds_until_reset()
        if wait <= 0:
            wait = 60  # safety floor — budget may have just reset
        # Cap at the idle-check interval rather than an hour: the loop is the
        # only thing that runs `periodic_maintenance`, so however long it sleeps
        # is how long submission checks sit idle — and those cost no simulation
        # budget. Waking to re-read the budget is free.
        wait = min(wait, CHECK_MAX_IDLE_SEC)
        elog.warning("Budget exhausted, sleeping %ds until reset", wait)
        time.sleep(wait)
        state["budget_exhausted"] = budget.is_exhausted()
        return

    if state["concurrent"] and not state["inflight"]:
        wait = _concurrent_backoff(state.get("concurrent_streak", 1))
        elog.info(
            "API concurrent limit full, sleeping %ds (streak=%d)",
            wait,
            state.get("concurrent_streak", 1),
        )
        state["concurrent"] = False
        time.sleep(wait)
        return

    if state["concurrent"]:
        state["concurrent"] = False
        time.sleep(45)
        return

    time.sleep(5 if not state["inflight"] else 3)
