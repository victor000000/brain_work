"""Reaction to an HTTP 429 from POST /simulations.

Split out of `core/api_retry.py`. The concurrent-limit and budget cases are
terminal — the caller returns the action verbatim; a transient rate limit
sleeps out its reset hint and asks the caller to loop again.
"""

import time

import core.budget as budget
from core.api_retry_headers import RATE_LIMIT_WAIT, _reset_seconds
from core.log import get_file_logger

slog = get_file_logger("submit")

BUDGET_RESET_THRESHOLD = 600  # >10 min reset likely means daily budget, not rate limit


def _handle_429(resp, batch_idx, attempt):
    """Return 'CONCURRENT', 'BUDGET', or None after sleeping for a retry.

    Reads the rate-limit headers regardless of branch — CONCURRENT 429s may
    still carry X-Ratelimit-Remaining and we want to react.
    """
    budget.update_from_headers(resp.headers)

    if "CONCURRENT" in resp.text:
        slog.debug("B%d: CONCURRENT — returning to poll loop", batch_idx)
        return "CONCURRENT"

    if budget.is_exhausted():
        slog.info("B%d: budget exhausted (from 429 headers)", batch_idx)
        return "BUDGET"

    # Large reset time (>10 min) indicates daily budget, not transient rate limit
    reset = _reset_seconds(resp)
    if reset > BUDGET_RESET_THRESHOLD:
        budget.mark_exhausted(reset)
        slog.info("B%d: large reset=%ds, treating as budget exhaustion", batch_idx, int(reset))
        return "BUDGET"

    # Transient rate limit — wait and retry
    slog.debug("B%d: rate limit, wait %.0fs (att %d)", batch_idx, max(reset, RATE_LIMIT_WAIT), attempt + 1)
    time.sleep(max(reset, RATE_LIMIT_WAIT))
    return None
