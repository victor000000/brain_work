"""The maxTrade/maxPosition pair for a region, split out of `settings_factory`."""

import random

from core.constraints import NO_MAX_POSITION_REGIONS


def _pick_trade_position(region):
    max_trade = random.choice(["ON", "OFF"])
    if region in NO_MAX_POSITION_REGIONS:
        return max_trade, "OFF"
    if max_trade == "ON":
        return max_trade, "OFF"
    return max_trade, random.choice(["ON", "OFF"])
