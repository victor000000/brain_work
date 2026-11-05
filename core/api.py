"""BRAIN API — the stable import path for the correlation helpers.

The pieces live in `core.api_poll` (Retry-After polling), `core.api_corr` (the
two fetches) and `core.api_gate` (the pass/fail decision); they are re-exported
here so `from core.api import ...` keeps working for every caller and test.
"""

from core.api_corr import (  # noqa: F401
    FETCH_ERROR,
    NOT_ELIGIBLE,
    get_prod_correlation,
    get_self_correlation,
)
from core.api_gate import _corr_passes, check_correlation_gate  # noqa: F401
from core.api_poll import (  # noqa: F401
    MIN_POLL_SLEEP_SEC,
    _poll_until_ready,
    _retry_after_seconds,
)

API = "https://api.worldquantbrain.com"
