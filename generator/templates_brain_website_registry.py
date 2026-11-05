"""The pool-based template registry: BRAIN website templates with operator tags.

Split out of `generator/templates_brain_website.py`, which re-exports
`TEMPLATES_BRAIN_WEBSITE` so `from generator.templates_brain_website import
TEMPLATES_BRAIN_WEBSITE` keeps resolving.
"""

from generator.templates_brain_website_group_cap import (
    cap_decile_neutralized,
    capm_beta,
    capm_residual,
    dual_bucket_neutralized,
    group_zscore_sector,
)
from generator.templates_brain_website_momentum import (
    momentum_66d,
    momentum_medium_term,
    price_momentum_xsec_ts,
    rank_momentum_sector,
    return_mean_20d,
    return_mean_reversion,
    ts_ir_trend,
    ts_rank_returns,
)
from generator.templates_brain_website_price_action import (
    high_low_spread,
    open_close_ratio,
    overnight_gap,
    vwap_close_spread,
    vwap_max_13d,
    vwap_max_strength,
)
from generator.templates_brain_website_reversion import (
    inverse_volatility,
    price_reversal_5d,
    price_reversal_short,
    price_zscore_20d,
    return_vol_20d,
    return_volatility,
)
from generator.templates_brain_website_transform import (
    hump_turnover_controlled,
    long_window_normalized,
    signed_power_transform,
    tail_extreme_signal,
    tvr_targeted_turnover,
    winsorized_signal,
)
from generator.templates_brain_website_volume import (
    covariance_divergence,
    double_gated_momentum,
    iv_skew_reversal,
    options_pcr_volume_gated,
    quality_gated_value,
    volume_gated_momentum,
    volume_surge,
)

# Template registry with operator tags
TEMPLATES_BRAIN_WEBSITE = [
    (price_zscore_20d, ["ts_mean", "ts_std_dev"]),
    (inverse_volatility, ["ts_std_dev"]),
    (overnight_gap, ["ts_delay"]),
    (volume_surge, ["rank", "ts_mean"]),
    (capm_residual, ["ts_regression", "group_mean", "rank", "ts_mean"]),
    (price_momentum_xsec_ts, ["group_rank", "rank", "ts_delta", "min"]),
    (return_mean_reversion, ["ts_mean", "ts_delay"]),
    (return_volatility, ["ts_std_dev", "ts_delay"]),
    (vwap_close_spread, []),
    (momentum_medium_term, ["ts_delta"]),
    (rank_momentum_sector, ["group_rank", "ts_delta"]),
    (ts_rank_returns, ["ts_rank"]),
    (high_low_spread, []),
    (open_close_ratio, ["rank"]),
    (vwap_max_strength, ["rank", "ts_max_diff"]),
    (price_reversal_short, ["ts_delta"]),
    (winsorized_signal, ["winsorize", "ts_backfill"]),
    (group_zscore_sector, ["group_mean", "group_std_dev"]),
    (cap_decile_neutralized, ["group_neutralize", "bucket", "rank"]),
    (volume_gated_momentum, ["trade_when", "ts_delta", "ts_mean"]),
    # Templates from data/templates_pv_option.json. Its `volume_gated_signal`,
    # `winsorized_backfilled_pattern` and `group_zscore_manual` entries are
    # already covered by `volume_gated_momentum`, `winsorized_signal` and
    # `group_zscore_sector` above — registering them twice would only weight
    # those shapes double.
    (capm_beta, ["ts_regression", "group_mean", "rank", "ts_mean"]),
    (return_mean_20d, ["ts_mean", "ts_delay"]),
    (return_vol_20d, ["ts_std_dev", "ts_delay"]),
    (momentum_66d, ["ts_delta"]),
    (vwap_max_13d, ["rank", "ts_max_diff"]),
    (price_reversal_5d, ["ts_delta"]),
    # `ts_delta` is in the tag because the PCR-less fallback emits it: options
    # data exists in USA/IND only, so the other regions take the branch that
    # gates a `ts_delta` instead of the pcr field. Measured 2026-10-09 over
    # brain_logs/alpha.log*: 31 of this template's 40 recorded alphas came from
    # that branch, e.g. `trade_when(rank(min_trade_volume_30m_pre_close_2 /
    # adv20) > 0.5, ts_delta(mean_last_trade_pr…` — so the tag was wrong for
    # most of its own output. `weighted_selection.get_weight` takes the minimum
    # usage over the declared operators, so an operator left out of the tag is
    # never counted against the template: it kept the full weight of the
    # under-used `trade_when`/`rank` pair on draws that mostly spent `ts_delta`.
    (options_pcr_volume_gated, ["trade_when", "rank", "ts_delta", "ts_mean"]),
    (signed_power_transform, ["signed_power"]),
    # From the operator-coverage census of 2026-10-12: of the platform's 83
    # supported operators, this generator had never emitted 22 of them, over
    # 49,415 recorded expressions. No mined skeleton uses the three registered
    # here either, so without a template the shapes cannot enter the pool at
    # all. Each carries an operator whose recorded usage is ~0, which is what
    # `weighted_selection.get_weight` rewards (it takes the minimum usage over
    # a template's tags) — but that is a side effect, not the argument: the
    # argument is that the shape space is unexplored and these are the forms
    # with a documented purpose.
    (ts_ir_trend, ["ts_ir"]),
    (hump_turnover_controlled, ["hump", "rank", "ts_delay"]),
    (covariance_divergence, ["ts_covariance", "rank"]),
    # The conjunction. Every `trade_when` in the registry gates on one
    # comparison; `and` is one of the operators with zero recorded emissions
    # and the multi-condition form is the community's, not an invention here.
    (double_gated_momentum, ["trade_when", "and", "rank", "ts_delta", "ts_mean"]),
    # The second turnover mechanism, on the same base signal as the first, so
    # the two are comparable: a fixed clip vs a targeted level.
    (tvr_targeted_turnover, ["ts_target_tvr_decay", "rank", "ts_delay"]),
    # The forum's prod-correlation shape: zero everything inside the group
    # z-score's ±1.1 band, keep the tails. PROD_CORRELATION is the check that
    # blocks most near-misses here, and this is the one forum post that reports
    # a shape working on it.
    (tail_extreme_signal, ["tail", "group_zscore"]),
    # The forum's other PC record, and the stronger one: a self-referential
    # slow gate with `nan` as the failed-branch value (no position), which no
    # other template here does. Retained earnings is out of scope for the gate
    # itself, so the proxy is trading activity.
    (quality_gated_value, ["trade_when", "greater", "ts_rank", "ts_backfill", "ts_mean"]),
    # The community's options shape, replicated parameter for parameter: a
    # submitted, OS-active IV skew. Emits in USA and IND only — the regions
    # that carry options data — and has no fallback branch by design.
    (iv_skew_reversal, ["rank", "ts_decay_linear", "ts_zscore", "ts_backfill"]),
    # The forum's dual-bucket recipe: the strongest ablation record in the
    # corpus (Sharpe 6.24, PC 0.79 → 0.68) and the only shape here that
    # neutralizes within a grid derived from the signal itself.
    (
        dual_bucket_neutralized,
        [
            "group_neutralize",
            "group_zscore",
            "group_cartesian_product",
            "bucket",
            "rank",
            "ts_std_dev",
            "ts_mean",
            "ts_delay",
        ],
    ),
    # The corpus's window finding, and the registry's own gap: its z-score
    # shapes cap at 63 days, and the same normalization at 250 measured
    # 1.59-1.80 with the 2Y leg at 1.15-1.60 — the check this account fails
    # most. One operator pair, deliberately.
    (long_window_normalized, ["rank", "ts_zscore"]),
]
