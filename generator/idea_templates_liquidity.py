"""Finite cost-aware reversal hypotheses; not registered or performance-proven.

The measured CHN candidate pwvERMjv passes the ordinary Sharpe/fitness gates
but fails robust-universe Sharpe. Its positive cost-rank multiplier tilts
relative closing pressure toward higher estimated transaction costs. The
complement tests the opposite tilt; it does not assume cost equals liquidity.
Canonical close/VWAP have matching price units. The verified pv106 cost field
is ranked before multiplication, keeping the weights dimensionless.
"""

COST_FIELD = "transaction_cost_percentile_10"


def low_cost_intraday_reversal(fields, _rng):
    """Test closing-pressure reversal weighted toward lower estimated costs."""
    if not {"close", "vwap", COST_FIELD} <= set(fields):
        return None
    return f"-(rank(((close - vwap) / vwap) * (1 - rank({COST_FIELD}))))"


def high_cost_reversal_control(fields, _rng):
    """Reproduce the measured candidate's cost orientation as a matched control."""
    if not {"close", "vwap", COST_FIELD} <= set(fields):
        return None
    return f"-(rank(((close - vwap) / vwap) * rank({COST_FIELD})))"


def unweighted_intraday_reversal_control(fields, _rng):
    """Remove the cost multiplier while retaining price roles and orientation."""
    if not {"close", "vwap"} <= set(fields):
        return None
    return "-(rank((close - vwap) / vwap))"


LIQUIDITY_IDEA_TEMPLATES = (low_cost_intraday_reversal,)
LIQUIDITY_CONTROL_TEMPLATES = (high_cost_reversal_control, unweighted_intraday_reversal_control)
