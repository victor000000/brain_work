"""Generate randomized simulation settings with diversity weighting.

Less-covered neutralizations/decays/truncations get higher probability.
"""

import random

import generator.diversity_weights as diversity
from core.constraints import ALLOWED_NEUT_BY_REGION
from core.log import get_file_logger
from generator.diversity_picker import weighted_pick
from runner.setting_pools import DECAYS, NEUTRALIZATIONS, TEST_PERIODS, TRUNCATIONS
from runner.settings_trade import _pick_trade_position

settings_log = get_file_logger("settings")

# Fail-closed fallback for regions absent from ALLOWED_NEUT_BY_REGION: the
# intersection of every known region's allowed set (the most restrictive
# common subset), never the full NEUTRALIZATIONS list.
_MOST_RESTRICTIVE_NEUT: set[str] = (
    set.intersection(*(set(v) for v in ALLOWED_NEUT_BY_REGION.values())) if ALLOWED_NEUT_BY_REGION else set()
)


def make_settings(region, universe, delay, neutralization=None, decay=None, truncation=None):
    """Generate settings weighted by inverse coverage.

    `neutralization` may be pre-picked by the caller (the explorer pre-picks
    so it can pass the value into `weighted_choice`'s cell_context). When None,
    auto-pick using the diversity weights.

    `decay` and `truncation` are the same idea one level down: the polish path
    overrides them to re-run a near-miss under a *settings* variant rather than
    a neutralization one (see `polish.variant_settings`). When None they are
    drawn as before, so every existing caller is unchanged.
    """
    if neutralization is None:
        neutralization = pick_neutralization(region)
    max_trade, max_position = _pick_trade_position(region)

    settings = {
        "instrumentType": "EQUITY",
        "region": region,
        "universe": universe,
        "delay": delay,
        "decay": decay
        if decay is not None
        else (weighted_pick(DECAYS, diversity._decay_weights) or random.choice(DECAYS)),
        "neutralization": neutralization,
        "truncation": truncation
        if truncation is not None
        else (weighted_pick(TRUNCATIONS, diversity._truncation_weights) or random.choice(TRUNCATIONS)),
        "maxTrade": max_trade,
        "maxPosition": max_position,
        "pasteurization": "ON",  # cnhkmcp: always ON for data quality
        "nanHandling": "OFF",  # cnhkmcp: OFF is standard
        "testPeriod": weighted_pick(TEST_PERIODS, diversity._test_period_weights) or random.choice(TEST_PERIODS),
        "unitHandling": "VERIFY",
        "language": "FASTEXPR",
        "visualization": False,
    }
    settings_log.debug(
        "Settings: %s/%s/d%d n=%s d=%d t=%s mt=%s mp=%s pa=%s nh=%s tp=%s",
        region,
        universe,
        delay,
        neutralization,
        settings["decay"],
        settings["truncation"],
        max_trade,
        max_position,
        settings["pasteurization"],
        settings["nanHandling"],
        settings["testPeriod"],
    )
    return settings


def pick_neutralization(region):
    """Pick a neutralization for the given region using diversity weights.

    Filters via ALLOWED_NEUT_BY_REGION (from OPTIONS /simulations) so
    region-specific gaps (e.g. MEA's small set, CHN's lack of STATISTICAL)
    don't produce 400 errors. Unknown regions fail closed: only the most
    restrictive common neutralization subset is used, never the full list.
    """
    allowed = ALLOWED_NEUT_BY_REGION.get(region)
    if allowed is None:
        settings_log.error(
            "Region %r not in ALLOWED_NEUT_BY_REGION; falling back to the most restrictive set",
            region,
        )
        allowed = _MOST_RESTRICTIVE_NEUT
    pool = [n for n in NEUTRALIZATIONS if n in allowed]
    if not pool:
        raise ValueError(f"No allowed neutralization for region {region!r}")
    return weighted_pick(pool, diversity._neutralization_weights) or random.choice(pool)


# Kept as a backward-compatible alias for any internal caller that still uses
# the old name. New code should import `pick_neutralization`.
_pick_neutralization = pick_neutralization
