"""Options hypotheses for bounded probes, with no performance claim.

Only the two catalogued at-the-money IV families below are eligible. A field
must have its explicit counterpart in the supplied MATRIX pool; neither idea
falls back to prices, Greeks, historical volatility or another dataset.
"""

# Verified in the 2026-10-16 field snapshot. Within each family both sides and
# tenors describe annualized ATM IV on the same scale. The newer option40
# ``*_volatility_*days`` aliases are deliberately absent: their descriptions
# mix percentages and decimals, so names alone cannot establish their scale.
_IV_FAMILIES = (
    ("implied_volatility_call_{}", "implied_volatility_put_{}"),  # option8
    ("opt40_ivcall{}", "opt40_ivput{}"),  # option40
)
_SKEW_TENORS = (10, 20, 30, 60, 90, 120, 150, 180, 270, 360, 720, 1080)
# Ordered calendar-day maturities. Do not combine arbitrary tenors or choose
# two fields independently: near/far orientation defines the hypothesis.
_TERM_TENORS = ((10, 30), (20, 60), (30, 90), (60, 180), (90, 270), (120, 360), (180, 720), (360, 1080))


def _iv_skew_pairs(fields):
    """Present (call, put) counterparts at the same maturity and dataset."""
    present = set(fields)
    return [
        (call.format(tenor), put.format(tenor))
        for call, put in _IV_FAMILIES
        for tenor in _SKEW_TENORS
        if call.format(tenor) in present and put.format(tenor) in present
    ]


def _iv_term_pairs(fields):
    """Present (near put IV, far put IV) within one catalogued dataset."""
    present = set(fields)
    return [
        (put.format(near), put.format(far))
        for _, put in _IV_FAMILIES
        for near, far in _TERM_TENORS
        if put.format(near) in present and put.format(far) in present
    ]


def iv_relative_skew_reversal(fields, rng):
    """Short unusually high same-tenor downside demand, relative to IV level.

    (put - call)/(put + call) is dimensionless and invariant to a common IV
    scale. Its own six-month z-score asks whether downside protection has
    become unusually expensive for this stock; five-day decay smooths it.
    This is a directional hypothesis to measure, not evidence of predictivity.
    Missing or zero-sum IV is left undefined rather than replaced with a
    price signal or a constant with an assumed volatility unit.
    """
    pairs = _iv_skew_pairs(fields)
    if not pairs:
        return None
    call, put = rng.choice(pairs)
    skew = f"({put} - {call}) / ({put} + {call})"
    return f"-rank(ts_decay_linear(ts_zscore({skew}, 126), 5))"


def iv_put_term_stress(fields, rng):
    """Short unusual front-end put IV relative to longer-term put IV.

    A near/far ratio from the same dataset is dimensionless. Its six-month
    z-score distinguishes a stock's temporary front-end stress from its
    usual term structure. Both operands are puts, so a changing call/put
    mix cannot masquerade as a term-structure move. No tenor's IV is divided
    by maturity: the fields already report annualized volatility.
    """
    pairs = _iv_term_pairs(fields)
    if not pairs:
        return None
    near, far = rng.choice(pairs)
    return f"-rank(ts_decay_linear(ts_zscore({near} / {far}, 126), 5))"


OPTIONS_IDEA_TEMPLATES = (iv_relative_skew_reversal, iv_put_term_stress)
