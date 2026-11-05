"""Check alpha by attempting POST /submit.

201 = accepted (may need verification)
403 = rejected, body contains full check results
429 = throttled, retry with backoff
"""

import time

from core.log import get_file_logger
from runner.http_retry import retry_after_or

API = "https://api.worldquantbrain.com"
clog = get_file_logger("check")

MAX_RETRIES = 3
REQUEST_TIMEOUT_SEC = 20
# Whole call (including Retry-After sleeps) is bounded by this deadline.
TOTAL_DEADLINE_SEC = 45
DEFAULT_429_WAIT = 10


def check_via_submit(session, alpha_id):
    """Try to submit with bounded retries. Returns (status_code, checks_list)."""
    deadline = time.monotonic() + TOTAL_DEADLINE_SEC
    last_status = None

    for attempt in range(MAX_RETRIES):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            clog.warning("Submit-check %s: deadline reached", alpha_id)
            break
        clog.debug("Submit-check %s (att %d)...", alpha_id, attempt + 1)
        try:
            resp = session.post(
                f"{API}/alphas/{alpha_id}/submit",
                timeout=min(REQUEST_TIMEOUT_SEC, max(remaining, 1)),
            )
        except Exception as e:
            clog.warning("Submit-check %s: request error (att %d): %s", alpha_id, attempt + 1, e)
            # A missing response cannot prove the mutation was not accepted.
            # The request journal owns subsequent GET reconciliation.
            return None, None

        clog.debug(
            "Submit-check %s: HTTP %d  rl_rem=%s rl_lim=%s",
            alpha_id,
            resp.status_code,
            resp.headers.get("X-RateLimit-Remaining-Hour", "?"),
            resp.headers.get("X-RateLimit-Limit-Hour", "?"),
        )

        if resp.status_code == 201:
            clog.info("Submit-check %s: HTTP 201 (accepted)", alpha_id)
            return 201, []

        if resp.status_code == 403:
            if not resp.content:
                clog.warning("Submit-check %s: 403 empty body", alpha_id)
                return 403, None
            try:
                checks = resp.json().get("is", {}).get("checks", [])
                clog.debug("Submit-check %s: HTTP 403 (%d checks)", alpha_id, len(checks))
                return 403, checks
            except Exception as e:
                clog.warning("Submit-check %s: 403 bad JSON (%d bytes): %s", alpha_id, len(resp.content), e)
                return 403, None

        if resp.status_code == 429:
            last_status = 429
            wait = retry_after_or(resp.headers, DEFAULT_429_WAIT)
            clog.debug("Submit-check %s: throttled (att %d), wait %.0fs", alpha_id, attempt + 1, wait)
            if attempt == MAX_RETRIES - 1:
                break
            if time.monotonic() + wait > deadline:
                clog.warning("Submit-check %s: Retry-After %.0fs exceeds deadline; giving up", alpha_id, wait)
                break
            time.sleep(wait)
            continue

        clog.warning("Submit-check %s: unexpected HTTP %d body=%s", alpha_id, resp.status_code, resp.text[:100])
        return resp.status_code, None

    clog.warning("Submit-check %s: gave up after retries (last status=%s)", alpha_id, last_status)
    if last_status is None:
        return None, None
    return last_status, None
