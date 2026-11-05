"""Adapt the request interval to the server's own rate-limit headers.

Split out of `download/session_throttle.py`, which re-exports `MIN_INTERVAL`
and mixes `_AdaptMixin` into `ThrottleMixin`.
"""

import os

from download.session_throttle_parse import _parse_delay

# Fastest interval between requests. The server also enforces a per-second cap
# (X-RateLimit-Limit-Second), so going below this mostly buys 429s.
MIN_INTERVAL = float(os.environ.get("BRAIN_MIN_REQUEST_INTERVAL", "0.5"))


class _AdaptMixin:
    def _adapt(self, resp):
        """Set the request interval from the server's own rate-limit headers.

        Thresholds are derived from `X-RateLimit-Limit-Minute` rather than
        hardcoded, because the previous fixed thresholds assumed roughly a
        60/min budget. On a 30/min budget "remaining > 15" still means half the
        minute is spent, so it sped *up* exactly when it should have held.

        Measured 2026-10-02: a single session sustains ~73 successful req/min
        against this host (with some 429s absorbed by retry), while the old
        thresholds delivered ~27/min. The limit is per account — three parallel
        sessions gave 1.4x throughput and 15x the 429s — so rate, not
        concurrency, is the lever.

        Override the floor with BRAIN_MIN_REQUEST_INTERVAL.
        """
        # The two budgets constrain the same interval, so each is computed
        # independently and the strictest wins. Setting `_interval` directly in
        # each branch let the minute rule silently overwrite the second rule.
        floor = MIN_INTERVAL
        interval = floor

        # Per-second: a hard burst cap. The official SDK checks this
        # (`vendor/ace_api/extracted/ace_lib.py:_check_rate_limit` sleeps a
        # second whenever `x-ratelimit-remaining-second` drops below 1); we
        # did not, which is what produced the 429s during the refresh.
        rs_raw = resp.headers.get("X-RateLimit-Remaining-Second")
        if rs_raw is not None:
            try:
                if int(rs_raw) < 1:
                    interval = max(interval, 1.0)
            except ValueError:
                pass

        # Per-minute: the sustained budget.
        rm_raw = resp.headers.get("X-RateLimit-Remaining-Minute")
        if rm_raw is not None:
            try:
                rm = int(rm_raw)
            except ValueError:
                rm = None
            if rm is not None:
                try:
                    limit = int(resp.headers.get("X-RateLimit-Limit-Minute"))
                except (TypeError, ValueError):
                    limit = 30
                if rm <= max(2, limit // 10):
                    # Nearly spent — respect the reset window.
                    reset = _parse_delay(resp.headers.get("RateLimit-Reset"))
                    if reset is None:
                        reset = 5.0
                    interval = max(interval, reset, floor * 4)
                elif rm <= limit // 3:
                    interval = max(interval, floor * 2)

        self._interval = interval
