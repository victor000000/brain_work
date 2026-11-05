"""Parse the rate-limit headers the throttle reacts to.

Split out of `download/session_throttle.py`, which re-exports these names.
"""

import email.utils
import math
import time
from datetime import UTC

# Retry-After is only meaningful on a retryable response; a 200 carrying one
# used to be silently re-issued.
RETRYABLE_STATUSES = frozenset({500, 502, 503, 504})

# A broken or hostile Retry-After must not park the refresh for hours.
MAX_RETRY_SLEEP = 300.0


def _parse_delay(value):
    """Parse a Retry-After / RateLimit-Reset value into seconds, or None.

    Accepts seconds (the common case, including a float) and an RFC 7231
    HTTP-date, which BRAIN sends on some throttles. Missing, empty and garbage
    values return None — the callers supply their own default, and a refresh
    must never die on an unparseable header.

    The result is clamped to MAX_RETRY_SLEEP. A hostile or buggy value such as
    `1e400` (inf) or a 20-digit string otherwise reached `_adapt`, which stores
    it as the request interval; `_throttle` then did `time.sleep(inf - gap)`
    and raised OverflowError on the next request.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        seconds = float(text)
    except ValueError:
        pass
    else:
        if not math.isfinite(seconds):
            return None
        return min(max(0.0, seconds), MAX_RETRY_SLEEP)
    try:
        dt = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delay = dt.timestamp() - time.time()
    if not math.isfinite(delay):
        return None
    return min(max(0.0, delay), MAX_RETRY_SLEEP)
