"""F3 priors recompute — package layout.

Reads alpha_results, groups by (template, region, universe, delay), computes
the Beta(1, 49) posterior mean per cell, writes the result to cell_priors.
Tier-2 quarantine: cells with K=5 rejections and 0 submissions (aggregating
over neutralization) are quarantined; lifts after M=24h or when hit_weight
recovers above 0.04 (2x prior mean).

Called from `runner.explore_helpers.periodic_maintenance` every CHECK_INTERVAL=50
alpha completions.

Public API:
  refresh_priors(conn) — recompute and persist cell_priors.
"""

from generator.priors_loader._constants import (
    _ALPHA,
    _BETA,
    _QUARANTINE_DURATION_SECONDS,
    _QUARANTINE_K,
    _RECOVERY_HIT_WEIGHT,
    _SATURATION_CAP_N,
)
from generator.priors_loader.pyramid_lookups import (
    alpha_max_multiplier as _alpha_max_multiplier,
)
from generator.priors_loader.pyramid_lookups import (
    load_pyramid_lookups as _load_pyramid_lookups,
)
from generator.priors_loader.refresh import refresh_priors

# Re-export private names so tests that reach into the module still work.
__all__ = [
    "_ALPHA",
    "_BETA",
    "_QUARANTINE_DURATION_SECONDS",
    "_QUARANTINE_K",
    "_RECOVERY_HIT_WEIGHT",
    "_SATURATION_CAP_N",
    "_alpha_max_multiplier",
    "_load_pyramid_lookups",
    "refresh_priors",
]
