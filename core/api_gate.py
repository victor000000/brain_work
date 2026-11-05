"""The correlation gate: decide from the two arms whether an alpha may submit.

Split out of `core/api.py`, which re-exports these names.
"""

from core.api_corr import FETCH_ERROR, NOT_ELIGIBLE, get_prod_correlation, get_self_correlation
from core.log import get_file_logger

alog = get_file_logger("alpha")


def _corr_passes(value, threshold):
    """True if this corr arm clears the gate. Fail closed on FETCH_ERROR."""
    if value == FETCH_ERROR:
        return False
    if value == NOT_ELIGIBLE:
        return True  # not eligible → submit will handle the actual check
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # Missing/non-numeric correlation: never treat as a pass.
        return False
    return value < threshold


def check_correlation_gate(session, alpha_id, threshold=0.7):
    """Check both prod and self correlation. Returns (passes, details).

    Fail closed on transient fetch errors so we don't submit a potentially
    correlated alpha. NOT_ELIGIBLE (412) still counts as a pass — the
    submission endpoint will run its own correlation check downstream.
    """
    prod = get_prod_correlation(session, alpha_id)
    self_c = get_self_correlation(session, alpha_id)
    prod_ok = _corr_passes(prod, threshold)
    self_ok = _corr_passes(self_c, threshold)
    passes = prod_ok and self_ok
    alog.info("Corr gate %s: prod=%s self=%s pass=%s", alpha_id, prod, self_c, passes)
    return passes, {"prod": prod, "self": self_c}
