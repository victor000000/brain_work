"""(region, universe, delay) config picker — count or yield mode."""

import random

import generator.diversity_weights as dw
from generator.diversity_picker._log import dlog
from generator.diversity_picker._yield_mode import yield_mode_enabled


def _select_weights(state):
    """Return (weights_map, default_weight, mode_label) per current env mode."""
    if yield_mode_enabled():
        return state.region_config_yield_weights, dw.YIELD_PRIOR_MEAN, "yield"
    return state.region_config_weights, 1.0, "count"


def weighted_pick_config(configs):
    """Pick a (region, universe, delay) config.

    Weighting depends on BRAIN_YIELD_WEIGHTING env var: default is inverse-
    coverage; with the var set, switches to Beta-Bernoulli posterior expected
    hit-rate.
    """
    if not configs:
        return None

    weights_map, default, mode = _select_weights(dw.get_state())
    weights = [weights_map.get(config, default) for config in configs]
    total = sum(weights)
    rand_val = random.random() * total
    cumulative = 0.0
    for i, config in enumerate(configs):
        cumulative += weights[i]
        if rand_val <= cumulative:
            dlog.debug(
                "Picked config %s/%s/d%d (mode=%s, weight=%.4f)",
                config[0],
                config[1],
                config[2],
                mode,
                weights[i],
            )
            return config
    return configs[-1]
