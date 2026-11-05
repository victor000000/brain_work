"""Fill open slots with new batches; back off on consecutive failures.

When recent passes returned CONCURRENT, the *sleep* between passes grows
(see sleep_logic.CONCURRENT_MAX). We still try one fresh submit per pass —
that's our probe for whether the slot pool has drained. The escalating
inter-pass sleep is what caps the wasted generation cost; per-pass we still
make forward progress the moment BRAIN frees a slot.

Submit failures are tracked across passes in `state["submit_fail_streak"]`;
the thresholds and their backoffs live in `runner.explore_loop.fill_backoff`.
"""

import time

import core.budget as budget
from runner.explore_helpers import generate_and_submit
from runner.explore_helpers._constants import BATCH_SIZE
from runner.explore_loop.constants import elog
from runner.explore_loop.fill_backoff import (  # noqa: F401
    SYSTEMIC_BACKOFF_SEC,
    SYSTEMIC_FAIL_LIMIT,
    TRANSIENT_BACKOFF_SEC,
    TRANSIENT_FAIL_LIMIT,
    pause_if_needed,
)
from runner.probe_requests import ingest_probe_requests

# Failures tolerated inside a single pass before we stop trying.
PASS_FAILURE_LIMIT = 3


def fill_slots(session, state, conn, max_concurrent):
    """Fill all available slots with new batches.

    Honors the terminal results from generate_and_submit:
      "CONCURRENT" — BRAIN's slot pool is full; pause this loop iteration.
      "BUDGET"     — sim budget exhausted; same.
      None         — generation/submit failed; tolerate up to PASS_FAILURE_LIMIT
                     in a row, then stop for this pass.
    A batch dict is enqueued; a dict with `budget_low` pauses new submits while
    keeping the accepted batch in flight.
    """
    now = time.time()
    if now < state.get("submit_backoff_until", 0.0):
        return

    ingest_probe_requests(conn)

    consecutive_fails = state.get("submit_fail_streak", 0) or 0
    session_fails = 0
    while len(state["inflight"]) < max_concurrent:
        remaining = budget.get_state().last_remaining
        tail = remaining is not None and 0 < remaining <= max_concurrent * BATCH_SIZE
        if tail and state["inflight"]:
            # BRAIN's remaining headers can omit other in-flight charges.
            # Drain them, then use single simulations through the final zero.
            break
        if tail:
            result = generate_and_submit(session, conn, state["batch_idx"], max_expressions=1)
        else:
            result = generate_and_submit(session, conn, state["batch_idx"])
        state["batch_idx"] += 1
        if result == "CONCURRENT":
            state["concurrent"] = True
            state["concurrent_streak"] = state.get("concurrent_streak", 0) + 1
            break
        if result == "BUDGET":
            state["budget_exhausted"] = True
            elog.warning("Budget exhausted at batch %d", state["batch_idx"])
            break
        if result is None:
            consecutive_fails += 1
            session_fails += 1
            state["submit_fail_streak"] = consecutive_fails
            if pause_if_needed(state, consecutive_fails):
                break
            if session_fails >= PASS_FAILURE_LIMIT:
                elog.debug("%d consecutive submit failures this pass, backing off", session_fails)
                break
            continue
        consecutive_fails = 0
        state["submit_fail_streak"] = 0
        # A successful enqueue means BRAIN accepted us — reset the streak so
        # the next CONCURRENT (if any) starts fresh from the base wait.
        state["concurrent_streak"] = 0
        state["inflight"].append(result)
        elog.debug("B%d submitted, %d in-flight", result["idx"], len(state["inflight"]))
        if isinstance(result, dict) and result.get("budget_low"):
            state["budget_exhausted"] = True
            elog.warning(
                "Budget low after B%d (remaining=%s); batch stays in flight, pausing new submits",
                result["idx"],
                result.get("budget_remaining"),
            )
            break
        time.sleep(1.5)
