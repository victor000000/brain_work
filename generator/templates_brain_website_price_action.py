"""Price-action templates for the pool-based BRAIN website registry.

Split out of `generator/templates_brain_website.py`, which re-exports these
names so `from generator.templates_brain_website import ...` keeps resolving.
"""

from generator.price_range_fields import pick_range_prices, pick_vwap_prices
from generator.templates_brain_website_pick import _pick_price, _pick_price_set


def overnight_gap(fields, rng):
    """Overnight gap return - microstructure signal."""
    # One dataset for the whole expression: independent draws pair prices
    # across datasets and the platform rejects the second operand at
    # `subtract` — 389 times since 2026-10-08, half of vwap_close_spread's
    # output. `_pick_price_set` returns None when no single dataset can supply
    # every role, and the independent draws below are the fallback.
    pair = _pick_price_set(fields, rng, "close", "open")
    if pair is not None:
        close, open_f = pair
    else:
        close = _pick_price(fields, rng, "close")
        open_f = _pick_price(fields, rng, "open")
    if close is None or open_f is None:
        return None
    return f"{open_f} / ts_delay({close}, 1) - 1"


def vwap_close_spread(fields, rng):
    """Close deviation from VWAP with the same explicit field context."""
    pair = pick_vwap_prices(fields, rng)
    if pair is None:
        return None
    close, vwap = pair
    return f"({close} - {vwap}) / {vwap}"


def high_low_spread(fields, rng):
    """Matched-window high/low range relative to its closing price."""
    triple = pick_range_prices(fields, rng)
    if triple is None:
        return None
    high, low, close = triple
    return f"({high} - {low}) / {close}"


def open_close_ratio(fields, rng):
    """Intraday price direction strength."""
    # One dataset for the whole expression: independent draws pair prices
    # across datasets and the platform rejects the second operand at
    # `subtract` — 389 times since 2026-10-08, half of vwap_close_spread's
    # output. `_pick_price_set` returns None when no single dataset can supply
    # every role, and the independent draws below are the fallback.
    pair = _pick_price_set(fields, rng, "open", "close")
    if pair is not None:
        open_f, close = pair
    else:
        open_f = _pick_price(fields, rng, "open")
        close = _pick_price(fields, rng, "close")
    if open_f is None or close is None or open_f == close:
        return None
    return f"rank(-(1 - {open_f} / {close}))"


def vwap_max_strength(fields, rng):
    """Proximity to the recent VWAP high indicates strength.

    `ts_max_diff`, not `ts_max`: the platform's operator list (the allowlist
    generation validates against) has no `ts_max`.
    """
    vwap = _pick_price(fields, rng, "vwap")
    if vwap is None:
        return None
    window = rng.choice([10, 13, 21])
    return f"rank(ts_max_diff({vwap}, {window}))"


def vwap_max_13d(fields, rng):
    """13-day VWAP high - strength indicator (see vwap_max_strength on ts_max_diff)."""
    vwap = _pick_price(fields, rng, "vwap")
    if vwap is None:
        return None
    return f"rank(ts_max_diff({vwap}, 13))"
