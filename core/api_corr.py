"""Production and self correlation fetches, and the sentinels they return.

Split out of `core/api.py`, which re-exports these names.
"""

from core.api_poll import _poll_until_ready
from core.log import get_file_logger

API = "https://api.worldquantbrain.com"
alog = get_file_logger("alpha")

# Sentinel values for correlation fetches. The previous interface used None
# for both "not eligible (HTTP 412)" and "transient fetch error" — and the
# gate then treated both as a pass, which let correlated alphas slip through
# during transient failures. Distinguish the two so callers can fail closed
# on errors but still skip the gate when the alpha simply isn't eligible.
NOT_ELIGIBLE = "NOT_ELIGIBLE"
FETCH_ERROR = "FETCH_ERROR"


def get_prod_correlation(session, alpha_id):
    """Get production correlation. Returns float, NOT_ELIGIBLE, or FETCH_ERROR."""
    try:
        resp = _poll_until_ready(session, f"{API}/alphas/{alpha_id}/correlations/prod", timeout=60)
        if resp.status_code == 412:
            alog.debug("Prod corr %s: HTTP 412 (not eligible)", alpha_id)
            return NOT_ELIGIBLE
        if resp.status_code != 200 or not resp.content:
            alog.debug("Prod corr %s: HTTP %d", alpha_id, resp.status_code)
            return FETCH_ERROR
        data = resp.json()
        max_corr = data.get("max")
        if max_corr is None:
            return FETCH_ERROR
        alog.debug("Prod corr %s: max=%s", alpha_id, max_corr)
        return max_corr
    except Exception as e:
        alog.warning("Prod corr %s failed: %s", alpha_id, e)
        return FETCH_ERROR


def get_self_correlation(session, alpha_id):
    """Get self correlation. Returns float, NOT_ELIGIBLE, or FETCH_ERROR.

    Note: an *empty* `records` list with HTTP 200 means "no other alphas to
    compare against" — that's a clean pass (0.0), not a fetch error. A body
    with no `records` key at all means the correlation is still computing
    (the poll timed out) and must fail closed as FETCH_ERROR, never 0.0.
    """
    try:
        resp = _poll_until_ready(session, f"{API}/alphas/{alpha_id}/correlations/self", timeout=60)
        if resp.status_code != 200 or not resp.content:
            alog.debug("Self corr %s: HTTP %d", alpha_id, resp.status_code)
            return FETCH_ERROR
        data = resp.json()
        if not isinstance(data, dict) or "records" not in data:
            alog.warning("Self corr %s: still computing (no records in response)", alpha_id)
            return FETCH_ERROR
        records = data.get("records")
        if records is None:
            alog.warning("Self corr %s: still computing (null records in response)", alpha_id)
            return FETCH_ERROR
        if not records:
            return 0.0
        max_corr = data.get("max")
        if isinstance(max_corr, bool) or not isinstance(max_corr, (int, float)):
            alog.warning("Self corr %s: non-numeric max=%r", alpha_id, max_corr)
            return FETCH_ERROR
        alog.debug("Self corr %s: max=%s", alpha_id, max_corr)
        return max_corr
    except Exception as e:
        alog.warning("Self corr %s failed: %s", alpha_id, e)
        return FETCH_ERROR
