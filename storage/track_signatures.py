"""Template signature patterns for expression identification.

Ordered by specificity -- first match wins.
Patterns map to template names tracked in template_performance.

High-perf templates (raw_regression, power_ratio, etc.) are matched
BEFORE generic patterns so they get distinct tracking.
"""

TEMPLATE_SIGNATURES = [
    # --- Registered shapes added 2026-10-12/13 ---
    # These come first because the list is first-match-wins and everything
    # below is a *legacy* vocabulary: an expression whose generation-time
    # attribution was lost — a reattached batch stored by a later process —
    # used to fall through to a legacy label (`peer_rank`, `zscore_basic`) or
    # to "unknown", which misattributes exactly the shapes whose records are
    # being read. Signatures are operator-distinctive, not keyword guesses.
    (r"ts_target_tvr_decay\(", "tvr_targeted_turnover"),
    (r"group_cartesian_product", "dual_bucket_neutralized"),
    (r"tail\(group_zscore", "tail_extreme_signal"),
    (r"trade_when\(and\(", "double_gated_momentum"),
    (r"trade_when\(greater\(", "quality_gated_value"),
    (r"ts_covariance\(rank\(", "covariance_divergence"),
    (r"hump\(", "hump_turnover_controlled"),
    (r"ts_ir\(", "ts_ir_trend"),
    (r"ts_decay_linear\(ts_zscore", "iv_skew_reversal"),
    (r"rank\(ts_zscore\([^,)]+,\s*250\)\)", "long_window_normalized"),
    # --- High-perf: specific patterns first for distinct tracking ---
    # zscore_delta_group: group_rank(zscore(ts_delta(rank(ts_zscore
    (r"group_rank\(zscore\(ts_delta", "zscore_delta_group"),
    # zscore_regression_decay: ts_regression * ts_decay_linear
    (r"ts_regression.*ts_decay_linear", "zscore_regression_decay"),
    # zscore_regression_long: ts_zscore with window >= 126
    (r"ts_regression\(ts_zscore\([^)]+,\s*(?:12[6-9]|1[3-9]\d|[2-9]\d\d)", "zscore_regression_long"),
    # raw_regression: ts_regression( NOT followed by ts_ (no zscore preprocessing)
    (r"ts_regression\((?!ts_)", "raw_regression"),
    # power_ratio: signed_power(field / (field + 0.01))
    (r"signed_power\((?!rank)[a-z].*?/.*?\+ 0\.01\)", "power_ratio"),
    # --- Momentum ---
    (r"ts_regression", "trend_strength"),
    (r"ts_decay_linear.*ts_delta", "recency_weighted_momentum"),
    (r"ts_covariance", "factor_comovement"),
    (r"ts_arg_max", "momentum_timing"),
    (r"ts_delay", "lagged_momentum"),
    (r"ts_rank", "percentile_momentum"),
    # --- Reversion ---
    (r"-rank\(ts_zscore", "zscore_reversion"),
    (r"ts_arg_min", "trough_proximity"),
    # --- Relative ---
    (r"group_neutralize", "sector_neutralized"),
    (r"group_rank", "peer_rank"),
    (r"group_scale", "peer_scaled"),
    (r"group_mean", "peer_mean_deviation"),
    (r"group_backfill", "peer_backfilled"),
    (r"winsorize", "winsorized_signal"),
    (r"quantile", "cross_quantile"),
    (r"zscore\(", "cross_zscore"),
    # --- Transform ---
    (r"log\(abs", "log_ratio"),
    (r"signed_power", "power_scaling"),
    (r"sqrt\(abs", "sqrt_dampened"),
    (r"inverse\(", "inverse_value"),
    (r"ts_std_dev", "low_vol_premium"),
    (r"ts_count_nans", "data_quality_signal"),
    # --- Conditional ---
    (r"trade_when", "trade_filter"),
    (r"is_nan", "nan_safe_momentum"),
    (r"days_from_last_change", "staleness_alpha"),
    (r"last_diff_value", "fresh_data_signal"),
    (r"ts_backfill", "gap_filled_signal"),
    (r"\?.*:", "ternary_regime"),
    # --- Typed ---
    (r"vec_avg", "vec_avg"),
    (r"densify", "densify"),
    (r"bucket", "bucket"),
    # --- Fallbacks ---
    (r"ts_delta", "momentum_basic"),
    (r"ts_mean", "vol_adjusted_signal"),
    (r"ts_zscore", "zscore_basic"),
]
