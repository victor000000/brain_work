"""Module-singleton state + the legacy module-attribute republishing trick.

External readers like `runner/settings_factory.py` and
`generator/diversity_picker.py` reach into the module via
`dw._neutralization_weights`-style attribute reads. After every cache swap
we re-bind those names on `generator.diversity_weights` (the package) so
they still resolve.
"""

import sys

from generator.diversity_weights.cache import DiversityCache

_state = DiversityCache()


def get_state() -> DiversityCache:
    return _state


def set_state(state: DiversityCache) -> None:
    global _state
    _state = state
    publish_module_attrs()


def publish_module_attrs() -> None:
    """Re-bind legacy module-level names so direct-attribute reads still work."""
    mod = sys.modules["generator.diversity_weights"]
    mod._region_config_weights = _state.region_config_weights
    mod._neutralization_weights = _state.neutralization_weights
    mod._decay_weights = _state.decay_weights
    mod._truncation_weights = _state.truncation_weights
    mod._test_period_weights = _state.test_period_weights
