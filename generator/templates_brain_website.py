"""Templates extracted from BRAIN website, forum, and cnhkmcp documentation.

These templates use only PV (price/volume) and options datafields, suitable for
generation when restricted to those datasets. Each template includes:
- Rationale: economic hypothesis behind the signal
- Typical settings: neutralization, decay, truncation
- Field requirements: what PV/options fields are needed

The templates follow the community-standard pipeline:
  clean → combine → neutralize → transform

These are the pool-based templates: each takes `(fields, rng)` — the region's
field pool and a `random.Random` — and picks its own operands by keyword,
because the roles differ (`close` vs `volume` vs `sector`) and the two-field
convention the cnhkmcp templates use cannot express that. A missing keyword is
not an error: the template returns None so generation falls back to a built-in,
rather than raising inside the RNG. See `generator.registry.template_uses_pool`.

The templates are grouped by economic role into siblings — `..._reversion`,
`..._momentum`, `..._price_action`, `..._group_cap`, `..._volume` and
`..._transform`, over the shared pickers in `..._pick` — and the tagged
registry lives in `..._registry`. All of them are re-exported here so
`from generator.templates_brain_website import ...` keeps resolving.
"""

from generator.templates_brain_website_group_cap import (  # noqa: F401
    cap_decile_neutralized,
    capm_beta,
    capm_residual,
    dual_bucket_neutralized,
    group_zscore_sector,
)
from generator.templates_brain_website_momentum import (  # noqa: F401
    momentum_66d,
    momentum_medium_term,
    price_momentum_xsec_ts,
    rank_momentum_sector,
    return_mean_20d,
    return_mean_reversion,
    ts_ir_trend,
    ts_rank_returns,
)
from generator.templates_brain_website_pick import (  # noqa: F401
    _GROUP_NAMES,
    _PRICE_EXCLUDE,
    _RAW_VOLUME_EXCLUDE,
    _pick,
    _pick_cap,
    _pick_group,
    _pick_price,
    _pick_return,
)
from generator.templates_brain_website_price_action import (  # noqa: F401
    high_low_spread,
    open_close_ratio,
    overnight_gap,
    vwap_close_spread,
    vwap_max_13d,
    vwap_max_strength,
)
from generator.templates_brain_website_registry import TEMPLATES_BRAIN_WEBSITE  # noqa: F401
from generator.templates_brain_website_reversion import (  # noqa: F401
    inverse_volatility,
    price_reversal_5d,
    price_reversal_short,
    price_zscore_20d,
    return_vol_20d,
    return_volatility,
)
from generator.templates_brain_website_transform import (  # noqa: F401
    hump_turnover_controlled,
    long_window_normalized,
    signed_power_transform,
    tail_extreme_signal,
    tvr_targeted_turnover,
    winsorized_signal,
)
from generator.templates_brain_website_volume import (  # noqa: F401
    covariance_divergence,
    double_gated_momentum,
    iv_skew_reversal,
    options_pcr_volume_gated,
    quality_gated_value,
    volume_gated_momentum,
    volume_surge,
)
