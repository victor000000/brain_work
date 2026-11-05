"""BRAIN HTTP session construction: default timeouts and the auth POST.

Split out of `core/auth.py`, which re-exports these names so callers and tests
keep importing them from the old path.
"""

import math
import os
import time

import requests

from core.log import get_file_logger

API_BASE = "https://api.worldquantbrain.com"

authlog = get_file_logger("auth")

# The auth endpoint allows 5 POSTs a minute — `X-RateLimit-Limit-Minute: 5` and
# `Retry-After` in the 429 body, both read off a live response on 2026-10-08.
# A spent window is not a credential problem, so it must not be reported as
# one: `get_session` turns a False from `_authenticate` into "no valid
# credentials or auth rejected" and exits. That is exactly how the explorer
# went down on 2026-10-08 — a restart spent the minute's 5 POSTs, every later
# start was refused, and the supervisor's fixed 15s respawn re-POSTed into the
# window that had just refused it, so the limit never lapsed.
AUTH_RATE_LIMIT_RETRIES = 2

# Longest `Retry-After` worth sleeping through inside a start-up call. A longer
# one is the supervisor's to ride out, not a blocking sleep here.
AUTH_RETRY_CAP_SEC = 90


# Attempts at the auth POST when the *request itself* fails, and the pause
# between them. A transport error is transient by nature and, unlike a 429,
# names no window to wait for — so a short retry is the whole remedy.
#
# Measured 2026-10-08, and it is the commoner of the two transient failures: 9
# transport errors against 5 rate limits across the day, all of them during an
# afternoon of platform latency, and each one cost a full explorer exit and a
# supervisor backoff cycle. A non-2xx that is not a 429 is still final — that
# is the platform answering, and the answer is about the credentials.
AUTH_TRANSPORT_RETRIES = 2
AUTH_TRANSPORT_BACKOFF_SEC = 3


def _retry_after(resp):
    """Seconds a 429 asks us to wait, or None when absent or not worth waiting."""
    try:
        wait = float(resp.headers.get("Retry-After"))
    except (AttributeError, TypeError, ValueError):
        return None
    return wait if 0 < wait <= AUTH_RETRY_CAP_SEC else None


def _auth_post(session):
    """POST /authentication, retrying a transport failure. None when all raised."""
    for attempt in range(AUTH_TRANSPORT_RETRIES + 1):
        try:
            return session.post(f"{API_BASE}/authentication")
        except Exception as err:
            if attempt == AUTH_TRANSPORT_RETRIES:
                authlog.error("Auth request failed after %d attempts: %s", attempt + 1, err)
                return None
            authlog.warning(
                "Auth request failed (attempt %d/%d), retrying: %s",
                attempt + 1,
                AUTH_TRANSPORT_RETRIES + 1,
                err,
            )
            time.sleep(AUTH_TRANSPORT_BACKOFF_SEC * (attempt + 1))
    return None


# requests has no default timeout, so a hung BRAIN endpoint would block a
# worker forever. (connect, read) — env override is parsed below.
DEFAULT_HTTP_TIMEOUT = (5, 30)
TIMEOUT_ENV_VAR = "BRAIN_HTTP_TIMEOUT"


def _parse_timeout(raw):
    """Parse BRAIN_HTTP_TIMEOUT: 'connect,read', or a single number for both.

    Returns (connect, read) floats, or None when unusable — a malformed env
    var must never break session creation.
    """
    if raw is None:
        return None
    parts = [p.strip() for p in str(raw).split(",")]
    try:
        values = tuple(float(p) for p in parts)
        if not all(math.isfinite(value) and value > 0 for value in values):
            return None
        if len(parts) == 1:
            return (values[0], values[0])
        if len(parts) == 2:
            return values
    except (TypeError, ValueError):
        return None
    return None


def _default_timeout():
    """Timeout from the environment when valid, else the built-in default."""
    return _parse_timeout(os.environ.get(TIMEOUT_ENV_VAR)) or DEFAULT_HTTP_TIMEOUT


class TimeoutSession(requests.Session):
    """requests.Session that injects a default (connect, read) timeout.

    Callers that pass an explicit `timeout=` keep it; everything else gets
    `default_timeout`. Drop-in for the bare sessions used before, including in
    tests that substitute fake session objects.
    """

    def __init__(self, default_timeout=None):
        super().__init__()
        self.default_timeout = _default_timeout() if default_timeout is None else default_timeout

    def request(self, method, url, *args, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.default_timeout
        return super().request(method, url, *args, **kwargs)


def _authenticate(session):
    """POST /authentication. Returns True on success.

    Neither transient failure is a statement about the credentials, and both
    are waited out rather than reported as one:

    * a **429** for as long as the endpoint's own `Retry-After` asks — see
      `AUTH_RATE_LIMIT_RETRIES`;
    * a **transport error** a fixed short number of times — see
      `AUTH_TRANSPORT_RETRIES`.

    Every other non-2xx is reported as-is and is final: that is the platform
    answering, and the answer is about the credentials.
    """
    for attempt in range(AUTH_RATE_LIMIT_RETRIES + 1):
        resp = _auth_post(session)
        if resp is None:
            return False
        if resp.status_code in (200, 201):
            authlog.info("Authenticated: HTTP %d user=%s", resp.status_code, resp.json().get("user", {}).get("id", "?"))
            return True
        wait = _retry_after(resp) if resp.status_code == 429 else None
        if wait is None or attempt == AUTH_RATE_LIMIT_RETRIES:
            authlog.error("Auth failed: HTTP %d %s", resp.status_code, resp.text[:100])
            return False
        authlog.warning("Auth rate limited (HTTP 429) — waiting %.0fs for the window", wait)
        time.sleep(wait)
    return False
