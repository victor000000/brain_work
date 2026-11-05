"""Circuit breaker for streaks of failed simulations.

When BRAIN has a bad window, freshly submitted batches come back `status=ERROR`
after MIN_ERROR_AGE_SEC without ever producing a child alpha. Each was accepted
with HTTP 201, so it is charged to the daily budget: continuing to fill slots
during the window spends simulations on nothing. Observed 2026-10-05 06:12-06:20
UTC: seven batches across five regions written off in eight minutes while the
account's remaining budget kept dropping.

Four consecutive ERROR-completed batches pause new submissions. The pause
doubles per further trigger (300s → 600s → ... capped at 1800s) and all state
resets on the first batch that completes with results. In-flight batches keep
running and are still polled — only *new* submissions are held.

The streak threshold assumes errors are sporadic, and the margin is narrower
than it looks: the occasional ~3-4% rate does occur, but measured batch error
rates are far higher on a bad day — 44% on 2026-10-03, 11% on 10-04, 27% on
10-05 (103 of ~376 batches), uniform across regions and settings, so the cause
is the platform rather than the expressions. At a 27% base rate four in a row
is p ≈ 0.5%, not 2e-6: still worth pausing for, but a large share of the 15
pauses seen on 10-05 is clustering rather than proof of a fresh window. Do not
tighten the threshold on the assumption that four in a row cannot be chance.

The pause is armed in `note_batch_done`, at the moment the fourth failure is
processed by the poll pass, not lazily by the fill gate that reads `paused()`:
the gate short-circuits on the budget/concurrent flags, and a pause that
depends on a later gate evaluation can miss its window entirely.
"""

import time

from runner.explore_loop.constants import elog

# Consecutive ERROR-completed batches that trigger a pause.
STREAK_LIMIT = 4
# First pause, doubled on each further streak while the window persists.
PAUSE_SEC = 300
PAUSE_MAX = 1800


def note_batch_done(state, failed: bool) -> None:
    """Update the streak for one completed batch; arm a pause at the limit."""
    if not failed:
        state["sim_error_streak"] = 0
        state["error_backoff_count"] = 0
        # Results mean the window is over: drop an armed pause too, or the
        # explorer would sit idle to the end of a 5-30 minute backoff after the
        # platform has demonstrably recovered.
        state["sim_error_pause_until"] = 0.0
        return

    streak = state.get("sim_error_streak", 0) + 1
    if streak < STREAK_LIMIT:
        state["sim_error_streak"] = streak
        return

    count = state.get("error_backoff_count", 0) + 1
    delay = min(PAUSE_SEC * 2 ** (count - 1), PAUSE_MAX)
    state["error_backoff_count"] = count
    state["sim_error_streak"] = 0
    state["sim_error_pause_until"] = time.time() + delay
    elog.warning(
        "Sim error streak %d: pausing new submissions for %ds (incident backoff %d)",
        streak,
        delay,
        count,
    )


def paused(state) -> bool:
    """True while an armed pause holds off new submissions.

    Also clears an expired timer, so the state dict never advertises a pause
    that is already over.
    """
    until = state.get("sim_error_pause_until", 0.0)
    if until > time.time():
        return True
    if until:
        state["sim_error_pause_until"] = 0.0
    return False
