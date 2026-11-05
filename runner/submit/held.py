"""Drain the held-alpha queue: retry cells that have left cooldown.

Split out of `runner/submit/flow.py`, which re-exports both names. The drain
is the one place the queue and the submit flow meet, so `check_and_submit` is
imported inside the function: `flow` re-exports this module, and resolving the
name at call time is also what lets tests stub `flow.check_and_submit`.
"""

import time

from core.log import get_file_logger
from runner.submit.throttle import _held_alphas, in_cooldown

clog = get_file_logger("check")

# Bound on held-alpha retries per maintenance pass.
DRAIN_PER_PASS = 3


def drain_held_queue(session, conn, now: float | None = None, max_submits: int = DRAIN_PER_PASS) -> int:
    """Retry held alphas for cells that have left cooldown, oldest cells first.

    Bounded per pass. Alphas whose retry is still throttled/held stay at the
    front of their queue for a later pass.
    """
    # Imported here, not at module level: flow imports this module to re-export
    # the drain, and the call has to see flow's (possibly patched) name.
    from runner.submit.flow import check_and_submit

    if now is None:
        now = time.time()
    attempts = 0
    for cell in list(_held_alphas.keys()):
        if attempts >= max_submits:
            break
        q = _held_alphas[cell]
        if not q or in_cooldown(cell, now):
            continue
        alpha_id = q.popleft()
        attempts += 1
        result = check_and_submit(session, conn, alpha_id)
        clog.info("HELD drain %s: %s", alpha_id, result)
        if result in ("HELD", "THROTTLED") and alpha_id not in q:
            q.appendleft(alpha_id)  # the HELD path may have re-queued it
    for cell in [c for c, q in _held_alphas.items() if not q]:
        del _held_alphas[cell]
    return attempts
