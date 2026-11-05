"""Dynamic diversity weighting — package layout.

Public API kept stable for callers that import from `generator.diversity_weights`.

State (per-dimension weight maps) lives on a `DiversityCache` singleton,
exposed via `get_state()`. Module-level legacy attributes
(`_region_config_weights`, `_neutralization_weights`, `_decay_weights`,
`_truncation_weights`, `_test_period_weights`) are re-bound on every
`load_diversity_weights` call so existing readers like
`runner/settings_factory.py` and `generator/diversity_picker.py` keep working
transparently — the publish_module_attrs trick lives in state.py.
"""

from generator.diversity_weights.cache import DiversityCache
from generator.diversity_weights.compute_count import (
    compute_config_weights as _compute_config_weights,
)
from generator.diversity_weights.compute_count import (
    compute_test_period_weights as _compute_test_period_weights,
)
from generator.diversity_weights.compute_count import (
    compute_weights as _compute_weights,
)
from generator.diversity_weights.loader import load_diversity_weights
from generator.diversity_weights.state import (
    get_state,
    publish_module_attrs,
    set_state,
)
from generator.diversity_weights.yield_weights import (
    YIELD_HIT_THRESHOLD,
    YIELD_PRIOR_ALPHA,
    YIELD_PRIOR_BETA,
    YIELD_PRIOR_MEAN,
    yield_weight,
)
from generator.diversity_weights.yield_weights import (
    compute_config_yield_weights as _compute_config_yield_weights,
)

# Initial publish so module-attr access works before the first
# load_diversity_weights call.
publish_module_attrs()

__all__ = [
    "YIELD_HIT_THRESHOLD",
    "YIELD_PRIOR_ALPHA",
    "YIELD_PRIOR_BETA",
    "YIELD_PRIOR_MEAN",
    "DiversityCache",
    "_compute_config_weights",
    "_compute_config_yield_weights",
    "_compute_test_period_weights",
    "_compute_weights",
    "get_state",
    "load_diversity_weights",
    "set_state",
    "yield_weight",
]
