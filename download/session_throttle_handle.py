"""Update rate state from a response and handle 429 / Retry-After.

Split out of `download/session_throttle.py`, which mixes `_HandleMixin` into
`ThrottleMixin`.
"""

import logging
import time

from download.session_throttle_parse import MAX_RETRY_SLEEP, RETRYABLE_STATUSES, _parse_delay

log = logging.getLogger("dl")


class _HandleMixin:
    def _handle(self, resp, url):
        """Process response: update rate state, handle 429 / Retry-After.

        Returning None asks the caller to retry. Only retryable statuses are
        retried — a 200 that happens to carry Retry-After is a success and is
        returned as-is.
        """
        self._last_req = time.time()
        self._adapt(resp)
        if resp.status_code == 429:
            wait_seconds = _parse_delay(resp.headers.get("RateLimit-Reset"))
            if wait_seconds is None:
                wait_seconds = _parse_delay(resp.headers.get("Retry-After"))
            if wait_seconds is None or wait_seconds < 2:
                wait_seconds = 2.0
            wait_seconds = min(wait_seconds, MAX_RETRY_SLEEP)
            log.warning("429 on %s — wait %.1fs", url, wait_seconds)
            time.sleep(wait_seconds)
            return None
        if resp.status_code in RETRYABLE_STATUSES:
            retry_after = _parse_delay(resp.headers.get("Retry-After"))
            if retry_after and retry_after > 0:
                if retry_after > MAX_RETRY_SLEEP:
                    log.warning("Retry-After %.0fs on %s capped to %.0fs", retry_after, url, MAX_RETRY_SLEEP)
                    retry_after = MAX_RETRY_SLEEP
                time.sleep(retry_after)
                return None
        return resp
