"""Read X-Ratelimit-* headers and reflect them onto the BudgetState singleton."""

import logging

from core.budget.state import BUDGET_FLOOR, get_state
from core.log import get_file_logger

# Two distinct loggers: a coarse one for end-user visibility (root-attached),
# and a budget-specific file logger for the rolling history.
log = logging.getLogger("brain")
blog = get_file_logger("budget")


def _parse_remaining(raw):
    """X-Ratelimit-Remaining → int, or None when absent/unparseable."""
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return None


def read_remaining(resp):
    """Return the parsed X-Ratelimit-Remaining as int, or None.

    None means the header was absent (unknown budget) or unparseable — never
    "exhausted". Accepts a requests-style response or a plain header mapping.
    """
    headers = getattr(resp, "headers", None)
    if headers is None:
        headers = resp
    try:
        raw = headers.get("X-Ratelimit-Remaining")
    except AttributeError:
        return None
    return _parse_remaining(raw)


def update_from_headers(headers):
    """Detect budget exhaustion from response headers (works on any response)."""
    rem_int = _parse_remaining(headers.get("X-Ratelimit-Remaining"))
    if rem_int is None:
        return  # missing or unparseable → unknown, never marks exhaustion
    get_state().note_remaining(rem_int)
    if rem_int < BUDGET_FLOOR:
        # The raw header value is handed straight to mark_exhausted, which
        # sanitizes it (non-finite/absurd/unparseable → a short default
        # window). Converting here instead would raise OverflowError on
        # "inf" and kill the submit path that just got a 201.
        get_state().mark_exhausted(headers.get("X-Ratelimit-Reset", "60"))


def _maybe_mark_exhausted(rem_int, reset_sec):
    """Translate a rate-limit reset header value into mark_exhausted on threshold."""
    if rem_int < BUDGET_FLOOR:
        get_state().mark_exhausted(reset_sec)


def check_budget(resp):
    """Read budget from response headers. Returns remaining or None."""
    remaining = resp.headers.get("X-Ratelimit-Remaining", None)
    limit = resp.headers.get("X-Ratelimit-Limit", "?")
    reset_sec = resp.headers.get("X-Ratelimit-Reset", "?")

    blog.debug("Budget: %s/%s remaining, resets in %ss", remaining, limit, reset_sec)
    rem_int = read_remaining(resp)
    if rem_int is None:
        # Missing header → unknown, not exhausted. Non-numeric stays raw.
        return remaining
    get_state().note_remaining(rem_int)

    _maybe_mark_exhausted(rem_int, reset_sec)

    if rem_int < BUDGET_FLOOR:
        blog.error("EXHAUSTED: %d/%s remaining, resets in %ss", rem_int, limit, reset_sec)
        log.warning("BUDGET EXHAUSTED: %d remaining", rem_int)
        return None
    if rem_int < 500:
        blog.warning("LOW: %d/%s remaining, resets in %ss", rem_int, limit, reset_sec)
    elif rem_int % 500 == 0:
        blog.info("Checkpoint: %d/%s remaining", rem_int, limit)
    return remaining
