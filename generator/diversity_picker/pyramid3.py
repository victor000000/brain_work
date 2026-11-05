"""Pyramid-3 target picker — score * yield_posterior (tiered).

A target row is only eligible when the chosen cell's field pool can satisfy
it. The score-weighted draw used to pick IND/d1 `option` ~12% of the time
even though that cell holds no option MATRIX fields, so the target silently
fell through to legacy picking. When no row is satisfiable the picker falls
back to the pv pyramid, which is always in scope.

The satisfiability scan and the posterior marginalization live in
`pyramid3_targets`; they are re-exported here so existing imports keep
resolving.
"""

import random

from generator.diversity_picker._log import dlog
from generator.diversity_picker.config_pick import weighted_pick_config
from generator.diversity_picker.pyramid3_targets import (  # noqa: F401
    _AVAILABLE_SQL,
    FALLBACK_CATEGORY,
    _available_categories,
    _eligible_rows,
    _max_posterior_per_rd,
)
from generator.priors_loader._constants import _YIELD_ALPHA, _YIELD_BETA

_PRIOR_MEAN = _YIELD_ALPHA / (_YIELD_ALPHA + _YIELD_BETA)

# Every eligible target row keeps at least this share of the strongest row's
# weight. Without it the allocation is winner-take-most: measured 2026-10-07,
# HKG/d1/pv took 60.1% of batches across 12 eligible rows, because
# `cell_yield_posterior` correctly says that cell yields 5-30x the others —
# and it then saturated on SELF_CORRELATION, failing four alphas at 0.77
# against a 0.70 limit the moment the submission cap lifted. The cell that
# produced every acceptance had become the one that could not be submitted.
#
# 0.10 moves HKG to 46.2% (0.05 would leave it at 56.7%, 0.20 would cut it to
# 31.2%) — still the largest single beneficiary, with the rest of the budget
# buying candidates whose return streams differ, which is what a
# correlation-bound submission gate needs. Raise or lower in one place.
EXPLORE_FLOOR = 0.10

# What a cell's yield record is worth in pyramid-score units, so a filled
# pyramid keeps a share instead of falling to exactly zero.
#
# `score = gap_to_3 * multiplier` reaches 0 as soon as a pyramid is filled, and
# `score * posterior` is then 0 whatever the posterior says. Measured
# 2026-10-10: HKG/d1/pv filled (16 alphas against a target of 3), scored 0, and
# the region that produced 328 of the 359 alphas above the floor in four days
# stopped being generated for 15 hours while the day's yield fell to 0.13%.
#
# Swept offline against a DB snapshot (`/tmp/pick_sweep.py`, 2,500 picks each,
# weight = (score + FILLED_CELL_SCORE) * posterior):
#
#     shipped (score > 0)   HKG  0.0%      eps=1.0   HKG 14.3%
#     filter relaxed only   HKG  1.1%      eps=2.0   HKG 17.4%
#     eps=0.5               HKG  9.5%      eps=4.5   HKG 22.0%
#                                          eps>=40   HKG ~25% (ceiling)
#
# The ceiling is proportional yield weighting and there is nothing to tune past
# it: HKG's posterior is 0.0328 against 0.0128 for the next cell, ~2.5x rather
# than the 5-30x recorded on 2026-10-07. The old "HKG at 46.2%" calibration
# came from a regime where HKG also carried an open pyramid gap, which it no
# longer has, so 46.2% is not reachable and not the target.
#
# 2.0 puts HKG at 17.4%, just under USA's 21.8% — reachable and competitive
# without abolishing the pyramid signal. Raise or lower in one place.
FILLED_CELL_SCORE = 2.0


def _weighted_choice(eligible):
    """Pick one (row, configs) pair weighted by score * max yield_posterior.

    `score` carries a floor (`FILLED_CELL_SCORE`) so a filled pyramid keeps a
    yield-weighted share rather than being unselectable.
    """
    max_post = _max_posterior_per_rd()
    weights = [(row[3] + FILLED_CELL_SCORE) * max_post.get((row[0], row[1]), _PRIOR_MEAN) for row, _cfgs in eligible]
    top = max(weights) if weights else 0.0
    if top > 0:
        weights = [max(w, EXPLORE_FLOOR * top) for w in weights]
    total = sum(weights)
    if total <= 0:
        return random.choice(eligible)
    rand_val = random.random() * total
    cumulative = 0.0
    for pair, w in zip(eligible, weights, strict=True):
        cumulative += w
        if rand_val <= cumulative:
            return pair
    return eligible[-1]


def pyramid3_weighted_pick(conn, configs):
    """Pick a (region, universe, delay, target_category) tuple.

      1. Selects a target pyramid (region, delay, category) weighted by
         score * cell_yield_posterior, keeping only categories the cell's
         field pool can satisfy.
      2. Picks a universe from the configs that satisfy that category,
         weighted by per-universe yield_posterior.
      3. Returns ((region, universe, delay), category).

    Falls back to weighted_pick_config + the pv pyramid when pyramid_targets
    is empty or no eligible (region, delay, category) row maps to the supplied
    configs. Always-on per design — no env var gating.
    """
    if not configs:
        return None, None
    eligible = _eligible_rows(conn, configs)
    if not eligible:
        return weighted_pick_config(configs), FALLBACK_CATEGORY

    row, universes_for_rd = _weighted_choice(eligible)
    category, score = row[2], row[3]

    # Pick universe weighted by per-cell yield_posterior (was uniform random).
    from generator.diversity_picker import yield_cache

    uni_weights = [yield_cache.posterior(r, u, d) for (r, u, d) in universes_for_rd]
    uni_total = sum(uni_weights)
    if uni_total > 0:
        r = random.random() * uni_total
        cum = 0.0
        cfg = universes_for_rd[-1]
        for c, w in zip(universes_for_rd, uni_weights, strict=True):
            cum += w
            if r <= cum:
                cfg = c
                break
    else:
        cfg = random.choice(universes_for_rd)

    dlog.debug(
        "pyramid3 picked %s/%s/d%d target=%s score=%.4f post=%.4f",
        cfg[0],
        cfg[1],
        cfg[2],
        category,
        score,
        yield_cache.posterior(*cfg),
    )
    return cfg, category
