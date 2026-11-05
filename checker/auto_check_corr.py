"""Correlation arms of the auto-check: the threshold and the preview's verdicts.

Split out of `checker/auto_check.py`, which re-exports these names.
"""

CORRELATION_LIMIT = 0.7

# The preview's check names, and the arm each one answers for.
_PREVIEW_CORRELATION_ARMS = {"PROD_CORRELATION": "prod", "SELF_CORRELATION": "self"}


def _preview_correlations(preview):
    """Correlation arms the preview already decided, as {arm: value}.

    Only a numeric value on a PASS/FAIL row counts. A `PENDING` row, or the
    `ERROR` the platform reports while its correlation computation is down,
    carries `value=None` and is left to the endpoint poll — an undecided arm
    must never be read as a pass.
    """
    out = {}
    for ch in preview or []:
        arm = _PREVIEW_CORRELATION_ARMS.get((ch.get("name") or "").upper())
        if arm is None or ch.get("result") not in ("PASS", "FAIL"):
            continue
        value = ch.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[arm] = value
    return out
