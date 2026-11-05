"""Constants and the template-call helper shared by the template tests."""

import random

from generator.registry import template_uses_pool
from generator.templates_brain_website import winsorized_signal

# One field per role the pool-based templates pick by keyword — real pv/option
# names, so the keyword filters match the way they do against a region pool.
# The implied-volatility pair is a same-tenor call/put set from one dataset,
# which is what `_pick_iv_skew_pair` requires; a lone call field would make
# `iv_skew_reversal` look like a template that never emits, and its tag test
# would then fail for the wrong reason.
POOL = [
    # A complete daily close/VWAP pair; retain mismatched windows below.
    "close",
    "vwap",
    "pv37_close_12",
    "pv37_volume_1430",
    "pv141_volume_ratio_wq_w_close_market",
    "pv37_vwap_14",
    "pv37_open_12",
    "pv37_high_140000",
    "pv37_low_163000",
    # A complete range family, alongside the partial/mismatched windows above.
    "pv37_high_1430",
    "pv37_low_1430",
    "pv37_close_1430",
    "pv37_cap_14",
    "pv20_sector_1964",
    "pv20_returns15_1001",
    "pcr_oi_180",
    "implied_volatility_call_20",
    "implied_volatility_put_20",
]

# Templates that take any field rather than picking by keyword: they still
# produce an expression from a pool that matches none of the usual keywords.
ANY_FIELD = {winsorized_signal}


def _call(fn, fields=None, rng=None):
    """Call a template under its own convention — `(f1, f2)` or `(fields, rng)`."""
    fields = POOL if fields is None else fields
    rng = random.Random(7) if rng is None else rng
    if template_uses_pool(fn):
        return fn(fields, rng)
    return fn(fields[0], fields[1])
