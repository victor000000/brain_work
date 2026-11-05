"""Mean-reversion and volatility templates for the BRAIN website registry.

Split out of `generator/templates_brain_website.py`, which re-exports these
names so `from generator.templates_brain_website import ...` keeps resolving.
"""

from generator.templates_brain_website_pick import _pick, _pick_price


def price_zscore_20d(fields, rng):
    """Classic 20-day price z-score - mean reversion signal."""
    close = _pick(fields, rng, "close")
    if close is None:
        return None
    return f"({close} - ts_mean({close}, 20)) / ts_std_dev({close}, 20)"


def inverse_volatility(fields, rng):
    """Inverse trailing volatility - low volatility anomaly."""
    returns = _pick(fields, rng, "return")
    if returns is None:
        return None
    return f"1.0 / ts_std_dev({returns}, 250)"


def return_volatility(fields, rng):
    """Recent return volatility as risk measure."""
    close = _pick_price(fields, rng, "close")
    if close is None:
        return None
    window = rng.choice([20, 40, 60])
    return f"ts_std_dev({close} / ts_delay({close}, 1) - 1, {window})"


def price_reversal_short(fields, rng):
    """Short-term price reversal for mean reversion."""
    close = _pick(fields, rng, "close")
    if close is None:
        return None
    window = rng.choice([3, 5, 10])
    return f"-ts_delta({close}, {window})"


def return_vol_20d(fields, rng):
    """20-day return volatility."""
    close = _pick_price(fields, rng, "close")
    if close is None:
        return None
    return f"ts_std_dev({close} / ts_delay({close}, 1) - 1, 20)"


def price_reversal_5d(fields, rng):
    """5-day price change, inverted for mean reversion."""
    close = _pick(fields, rng, "close")
    if close is None:
        return None
    return f"-ts_delta({close}, 5)"
