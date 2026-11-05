"""Retry-After polling shared by the BRAIN API helpers.

Split out of `core/api.py`, which re-exports both names so callers and tests
that reach for `core.api._poll_until_ready` keep working.
"""

import math
import time

from core.log import get_file_logger

alog = get_file_logger("alpha")

# Floor on the time between polls of a Retry-After endpoint. See
# `_poll_until_ready`: the platform's `Retry-After: 1` on the correlation
# endpoints is a "still queued" hint, not a promise that a second's wait
# produces anything.
MIN_POLL_SLEEP_SEC = 5.0


def _retry_after_seconds(resp):
    """Parse Retry-After (seconds or HTTP date) defensively. None on failure.

    Non-finite values are treated as absent: `time.sleep(nan)` raises and a
    truthy `inf` would only ever be swallowed by the caller's guard.
    """
    retry = resp.headers.get("Retry-After")
    if not retry:
        return None
    try:
        value = float(retry)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return max(value, 0.0)


def _poll_until_ready(session, url, timeout=120):
    """Poll URL until Retry-After is 0. Gives up after timeout seconds.

    A timed-out poll may return an in-progress body — callers must check the
    body, not assume it holds a result.

    The wait is floored at MIN_POLL_SLEEP_SEC. The correlation endpoints answer
    `Retry-After: 1` while the computation is queued and will keep saying it for
    minutes, so honouring it literally spends the whole deadline issuing a
    request a second and still returns nothing — measured 2026-10-06, 59 polls
    in 90s against `/correlations/prod`, every one `Retry-After: 1.0`, body
    empty. That is 120 wasted requests per alpha across the two arms, aimed at
    an endpoint that is already congested, i.e. the polling was feeding the
    problem it was waiting on.
    """
    deadline = time.time() + timeout
    while True:
        resp = session.get(url)
        retry = _retry_after_seconds(resp)
        if not retry:
            return resp
        if time.time() + retry > deadline:
            alog.warning("Poll timeout after %ds: %s", timeout, url)
            return resp
        time.sleep(max(retry, MIN_POLL_SLEEP_SEC))
