"""Probe-only mean-displacement hypotheses inspired by a community ablation.

Source: BRAIN community post 44089095804439 (retrieved 2026-10-16), which
compares rolling-mean displacement followed by a historical quantile with
either transform alone. Its fundamental ratios are outside this project's
scope. These unmeasured adaptations use canonical daily prices instead.

The 168/252-day windows are fixed in advance. An outer rank makes a monotone
quantile-driver change redundant as an experiment; keep the default driver.
Standalone displacement and quantile controls use the same roles and windows.
"""

DISPLACEMENT_WINDOW = 168
QUANTILE_WINDOW = 252


def anchored_price_quantile(fields, _rng):
    """Rank a stock's current mean displacement against its own history.

    The historical quantile compares one price series with itself, so its
    final output is dimensionless despite the displacement having price units.
    This measures relative strength; its negative is a separate reversal probe.
    """
    if "close" not in fields:
        return None
    return f"rank(ts_quantile(ts_av_diff(close, {DISPLACEMENT_WINDOW}), {QUANTILE_WINDOW}))"


def anchored_close_vwap_quantile(fields, _rng):
    """Apply the same transform to close relative to the session's VWAP.

    Both operands are canonical daily price fields. Their ratio is
    dimensionless before either time-series transform. This tests whether
    relative closing pressure contributes beyond nominal price displacement.
    """
    if "close" not in fields or "vwap" not in fields:
        return None
    return f"rank(ts_quantile(ts_av_diff(close / vwap, {DISPLACEMENT_WINDOW}), {QUANTILE_WINDOW}))"


def price_displacement_only(fields, _rng):
    """Control for the mean-displacement layer without historical quantiles."""
    if "close" not in fields:
        return None
    return f"rank(ts_av_diff(close, {DISPLACEMENT_WINDOW}))"


def price_quantile_only(fields, _rng):
    """Control for historical price position without mean displacement."""
    if "close" not in fields:
        return None
    return f"rank(ts_quantile(close, {QUANTILE_WINDOW}))"


def close_vwap_displacement_only(fields, _rng):
    """Control for mean displacement of relative closing pressure."""
    if "close" not in fields or "vwap" not in fields:
        return None
    return f"rank(ts_av_diff(close / vwap, {DISPLACEMENT_WINDOW}))"


def close_vwap_quantile_only(fields, _rng):
    """Control for historical relative closing pressure without centering."""
    if "close" not in fields or "vwap" not in fields:
        return None
    return f"rank(ts_quantile(close / vwap, {QUANTILE_WINDOW}))"


DISPLACEMENT_IDEA_TEMPLATES = (anchored_price_quantile, anchored_close_vwap_quantile)
DISPLACEMENT_CONTROL_TEMPLATES = (
    price_displacement_only,
    price_quantile_only,
    close_vwap_displacement_only,
    close_vwap_quantile_only,
)
