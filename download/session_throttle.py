"""Rate-limit throttle mixin for BrainSession.

The pieces live in `download.session_throttle_parse` (the header parsing and
the limits it clamps to), `download.session_throttle_adapt` (the interval rule)
and `download.session_throttle_handle` (429 / Retry-After handling); they are
re-exported here so `from download.session_throttle import ...` keeps working
for every caller and test. `_throttle` stays in this module — it reads `time`
from this namespace.
"""

import logging
import time

from download.session_throttle_adapt import MIN_INTERVAL, _AdaptMixin  # noqa: F401
from download.session_throttle_handle import _HandleMixin
from download.session_throttle_parse import (  # noqa: F401
    MAX_RETRY_SLEEP,
    RETRYABLE_STATUSES,
    _parse_delay,
)

log = logging.getLogger("dl")


class ThrottleMixin(_AdaptMixin, _HandleMixin):
    """Mixin providing adaptive rate-limit methods.

    Expects the host class to have:
      _last_req: float   — timestamp of last request
      _interval: float   — minimum seconds between requests
    """

    def _throttle(self):
        """Sleep if needed to respect rate limits."""
        gap = time.time() - self._last_req
        if gap < self._interval:
            time.sleep(self._interval - gap)
