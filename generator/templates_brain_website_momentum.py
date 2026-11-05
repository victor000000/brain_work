"""Momentum and return templates for the BRAIN website registry.

Split out of `generator/templates_brain_website.py`, which re-exports these
names so `from generator.templates_brain_website import ...` keeps resolving.
"""

from generator.templates_brain_website_pick import _pick, _pick_group, _pick_price, _pick_return


def price_momentum_xsec_ts(fields, rng):
    """Intersection of cross-sectional and time-series momentum."""
    close = _pick(fields, rng, "close")
    sector = _pick_group(rng)
    if close is None:
        return None
    window = rng.choice([44, 66, 88])
    return f"min(group_rank({close}, {sector}), rank(ts_delta({close}, {window})))"


def return_mean_reversion(fields, rng):
    """Short-term return mean reversion."""
    close = _pick_price(fields, rng, "close")
    if close is None:
        return None
    window = rng.choice([5, 10, 20])
    return f"-ts_mean({close} / ts_delay({close}, 1) - 1, {window})"


def momentum_medium_term(fields, rng):
    """Medium-term momentum (2-3 months)."""
    close = _pick(fields, rng, "close")
    if close is None:
        return None
    window = rng.choice([44, 66, 88])
    return f"ts_delta({close}, {window})"


def rank_momentum_sector(fields, rng):
    """Relative momentum within sector."""
    close = _pick(fields, rng, "close")
    sector = _pick_group(rng)
    if close is None:
        return None
    window = rng.choice([20, 40, 66])
    return f"group_rank(ts_delta({close}, {window}), {sector})"


def ts_rank_returns(fields, rng):
    """Current return percentile vs own history."""
    returns = _pick(fields, rng, "return")
    if returns is None:
        return None
    window = rng.choice([126, 189, 252])
    return f"ts_rank({returns}, {window})"


def return_mean_20d(fields, rng):
    """20-day average daily return."""
    close = _pick_price(fields, rng, "close")
    if close is None:
        return None
    return f"ts_mean({close} / ts_delay({close}, 1) - 1, 20)"


def momentum_66d(fields, rng):
    """66-day (~3 month) price momentum."""
    close = _pick(fields, rng, "close")
    if close is None:
        return None
    return f"ts_delta({close}, 66)"


def ts_ir_trend(fields, rng):
    """Risk-adjusted trend: the information ratio of a return series.

    `ts_ir(x, d)` is the platform's own `ts_mean(x, d) / ts_std_dev(x, d)` — a
    Sharpe over the window — and it is one of the 22 operators this generator
    has never emitted: measured 2026-10-12 over 49,415 recorded expressions,
    zero uses, against 9,250 for `ts_mean` and 3,067 for `ts_std_dev`, the two
    halves it is built from. No mined skeleton uses it either, so a registry
    template is the only way the shape enters the pool at all.

    The input is a return series and not a price: the ratio is only
    Sharpe-like when the window's mean and deviation are both returns, which is
    why the role is `_pick_return` rather than a substring match on "return" —
    the latter admits `return_on_equity` and its family.
    """
    returns = _pick_return(fields, rng)
    if returns is None:
        return None
    window = rng.choice([20, 60, 120, 250])
    return f"ts_ir({returns}, {window})"
