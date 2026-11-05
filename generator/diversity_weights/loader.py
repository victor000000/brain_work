"""Top-level load_diversity_weights — refresh all weight maps from alpha_results."""

import time

from core.log import get_file_logger
from generator.diversity_weights.compute_count import (
    compute_config_weights,
    compute_test_period_weights,
    compute_weights,
)
from generator.diversity_weights.state import get_state, publish_module_attrs
from generator.diversity_weights.yield_weights import compute_config_yield_weights

dlog = get_file_logger("diversity")

# Skip redundant reloads within this many seconds. Generators previously
# triggered a full recompute on every batch; now the explorer's maintenance
# pass owns the documented refresh cadence (force=True) while ad-hoc
# generate_expressions calls hit the cache.
DIVERSITY_TTL_SECONDS = 60


def load_diversity_weights(conn, force=False):
    """Load coverage counts and compute inverse + yield weights (TTL-cached).

    Always loads count-based weights (legacy). Also computes yield-based
    Beta-Bernoulli posterior weights — these are only consumed when
    `BRAIN_YIELD_WEIGHTING=1` is set in the environment (see
    diversity_picker.weighted_pick_config).

    Pass force=True from periodic_maintenance to bypass the TTL cache.
    """
    state = get_state()
    if not force and state.region_config_weights and (time.time() - state.loaded_at) < DIVERSITY_TTL_SECONDS:
        return
    state.neutralization_weights = compute_weights(conn, "neutralization")
    state.decay_weights = compute_weights(conn, "decay")
    state.truncation_weights = compute_weights(conn, "truncation")
    state.test_period_weights = compute_test_period_weights(conn)
    state.region_config_weights = compute_config_weights(conn)
    state.region_config_yield_weights = compute_config_yield_weights(conn)
    state.loaded_at = time.time()
    publish_module_attrs()

    dlog.debug(
        "Diversity weights: %d configs, %d yield-configs, %d neut, %d dec, %d tru, %d tp",
        len(state.region_config_weights),
        len(state.region_config_yield_weights),
        len(state.neutralization_weights),
        len(state.decay_weights),
        len(state.truncation_weights),
        len(state.test_period_weights),
    )
