"""Retry-After parsing for the POST loop, and its response logging.

Split out of `core/api_retry.py`, which re-exports these names so tests and
callers keep importing them from the old path.
"""

import logging
import math
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from core.log import get_file_logger

log = logging.getLogger("brain")
slog = get_file_logger("submit")

RATE_LIMIT_WAIT = 10  # minimum wait on a transient 429


def _retry_after_seconds(resp):
    """Parse a Retry-After header (int seconds or HTTP date) into seconds.

    Never raises: returns None when absent or unparseable.
    """
    raw = resp.headers.get("Retry-After")
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        pass
    else:
        # "inf"/"nan" parse as floats but would poison later arithmetic (and
        # time.sleep(nan) raises), so treat them as an absent header.
        return max(value, 0.0) if math.isfinite(value) else None
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max((when - datetime.now(UTC)).total_seconds(), 0.0)


def _reset_seconds(resp):
    """Wait hint from headers: Retry-After, then X-Ratelimit-Reset, then default.

    Never raises — a malformed header falls through to the next source.
    """
    wait = _retry_after_seconds(resp)
    if wait is not None:
        return wait
    raw = resp.headers.get("X-Ratelimit-Reset")
    if raw is not None:
        try:
            value = float(str(raw).strip())
        except (TypeError, ValueError):
            value = None
        if value is not None and math.isfinite(value):
            return max(value, 0.0)
    return float(RATE_LIMIT_WAIT)


def _log_response(resp, batch_idx, attempt):
    """Log response code and rate limit headers."""
    slog.debug(
        "B%d att=%d: HTTP %d  daily=%s/%s  reset=%ss",
        batch_idx,
        attempt + 1,
        resp.status_code,
        resp.headers.get("X-Ratelimit-Remaining", "?"),
        resp.headers.get("X-Ratelimit-Limit", "?"),
        resp.headers.get("X-Ratelimit-Reset", "?"),
    )


def _give_up(resp, batch_idx):
    """Log a non-retryable response and return None for the caller."""
    slog.error("B%d: HTTP %d body=%s", batch_idx, resp.status_code, resp.text[:150])
    log.error("B%d: HTTP %d %s", batch_idx, resp.status_code, resp.text[:120])
    return None
