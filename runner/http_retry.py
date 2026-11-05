"""Safe Retry-After parsing shared by the poll and check paths.

RFC 7231 allows Retry-After to be either an integer number of seconds or an
HTTP-date. `float(header)` raises on the date form, so every caller must go
through this helper — it never raises and returns None for anything it cannot
make sense of (unknown values must not be treated as "no wait").
"""

import math
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


def parse_retry_after(headers) -> float | None:
    """Return a non-negative wait in seconds from a Retry-After header.

    Accepts int/float seconds and HTTP-dates. Returns None when the header is
    absent or unparseable; never raises.
    """
    try:
        raw = headers.get("Retry-After") if headers is not None else None
        if raw is None:
            return None
        try:
            value = float(raw)
            if not math.isfinite(value):
                return None
            return max(value, 0.0)
        except (TypeError, ValueError):
            pass
        try:
            parsed = parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return max((parsed - datetime.now(UTC)).total_seconds(), 0.0)
    except Exception:
        # Defensive: header accessors on exotic response objects must never
        # be able to kill the caller's loop.
        return None


def retry_after_or(headers, default: float) -> float:
    """parse_retry_after with a fallback used for pacing decisions."""
    value = parse_retry_after(headers)
    return default if value is None else value
