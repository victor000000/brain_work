"""Preview alpha checks via GET /check (fallback method).

Async checks may remain PENDING — use check_via_submit as primary.
"""

import time

from core.log import get_file_logger
from runner.http_retry import parse_retry_after, retry_after_or

API = "https://api.worldquantbrain.com"
clog = get_file_logger("check")

# The first GET triggers the computation and returns an empty body; the body
# lands when the platform finishes, not ~15s later as this once assumed.
# Measured 2026-10-08 UTC: a script polling npP7XkAq got an empty body on every
# poll for 28.8s and the body at 31.2s — so the computation alone can run past
# 30s. The *trigger* can also be delayed: in the explorer a check spent ~24s in
# 429 waits before its first 200, and none of that time starts the computation.
# Under 45s the deadline fired while the body was still due (observed: trigger
# at t=23.7s, body due ~t=55s, timeout at t=45s) — every one of those checks
# was paid for in full and then thrown away. 90s covers a late trigger plus a
# ~31s computation; the call stays bounded, which is what the guarantee below
# promises.
MAX_POLL_SECONDS = 90
REQUEST_TIMEOUT_SEC = 20
DEFAULT_429_WAIT = 10
EMPTY_BODY_WAIT_SEC = 8


def check_via_get(session, alpha_id):
    """Preview checks. Returns check list or None.

    The whole call is bounded by MAX_POLL_SECONDS wall-clock: 429 waits and
    Retry-After sleeps can never extend it (and can never loop forever).
    """
    clog.debug("GET-check %s...", alpha_id)
    start = time.monotonic()
    deadline = start + MAX_POLL_SECONDS
    resp = None

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            clog.warning("GET-check %s: timed out after %.0fs", alpha_id, time.monotonic() - start)
            return None
        try:
            resp = session.get(
                f"{API}/alphas/{alpha_id}/check",
                timeout=min(REQUEST_TIMEOUT_SEC, max(remaining, 1)),
            )
        except Exception as e:
            clog.warning("GET-check %s: error: %s", alpha_id, e)
            return None

        if resp.status_code == 429:
            wait = min(retry_after_or(resp.headers, DEFAULT_429_WAIT), max(deadline - time.monotonic(), 0))
            if wait <= 0:
                clog.warning("GET-check %s: throttled and out of time after %.0fs", alpha_id, time.monotonic() - start)
                return None
            clog.debug("GET-check %s: throttled, wait %.0fs", alpha_id, wait)
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            clog.warning("GET-check %s: HTTP %d", alpha_id, resp.status_code)
            return None

        # For a never-checked alpha the first GET triggers the computation and
        # returns an empty body; poll until it lands or the deadline passes.
        #
        # The platform sends `Retry-After` on that empty body to say when to
        # come back (measured: 1.0s). Honouring it — with the fixed wait kept
        # only as a fallback for a header-less response — is what makes the
        # polls dense enough to catch the body when it lands; at a flat 8s a
        # 90s deadline only affords ~11 looks at a computation that can take
        # 31s to appear.
        if not resp.content:
            wait = min(retry_after_or(resp.headers, EMPTY_BODY_WAIT_SEC), max(deadline - time.monotonic(), 0))
            if wait <= 0:
                clog.warning("GET-check %s: timed out after %.0fs (empty body)", alpha_id, time.monotonic() - start)
                return None
            clog.debug("GET-check %s: empty body, retrying in %.0fs", alpha_id, wait)
            time.sleep(wait)
            continue

        retry = parse_retry_after(resp.headers)
        if not retry or retry <= 0:
            break
        wait = min(retry, max(deadline - time.monotonic(), 0))
        if wait <= 0:
            clog.warning("GET-check %s: timed out after %.0fs", alpha_id, time.monotonic() - start)
            break
        time.sleep(wait)

    if not resp.content:
        clog.warning("GET-check %s: empty response body", alpha_id)
        return None
    try:
        return resp.json().get("is", {}).get("checks", [])
    except Exception as e:
        clog.warning("GET-check %s: parse error (%d bytes): %s", alpha_id, len(resp.content), e)
        return None
