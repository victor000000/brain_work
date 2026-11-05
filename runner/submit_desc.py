"""The structured 3-line description BRAIN requires on every alpha.

Split out of `runner/submit_checks.py`, which re-exports `ensure_description`
— `runner/submit/flow.py` imports it from there on the path to a submit.
"""

from core.api_properties import patch_alpha_description


def ensure_description(session, alpha_id, conn):
    """Add structured 3-line description (cnhkmcp format)."""
    row = conn.execute(
        "SELECT expression, region, neutralization FROM alpha_results WHERE alpha_id=?",
        (alpha_id,),
    ).fetchone()
    if not row:
        return
    _expr, region, neut = row

    desc = (
        f"Idea: Systematic factor signal combining cross-sectional "
        f"and time-series operators for {region} equities.\n"
        f"Rationale for data used: High-coverage data fields "
        f"selected for strong cross-sectional variation.\n"
        f"Rationale for operators used: Regression, ranking, "
        f"and {neut or 'market'} neutralization for robust signal."
    )
    patch_alpha_description(session, alpha_id, desc)
