"""Validation rules — valid operators and skip tokens for expression checking."""

# fmt: off
VALID_OPS = {
    # Arithmetic
    "add", "subtract", "multiply", "divide", "power", "signed_power",
    # Unary math
    "abs", "log", "sqrt", "sign", "reverse", "inverse", "densify",
    # Scaling / normalization
    "scale", "rank", "quantile", "normalize", "zscore", "winsorize",
    "min", "max", "bucket",
    # Group operations
    "group_backfill", "group_mean", "group_neutralize",
    "group_rank", "group_scale", "group_zscore",
    # Logic / comparison
    "if_else", "and", "or", "not",
    "less", "less_equal", "greater", "greater_equal",
    "equal", "not_equal", "is_nan",
    # Time-series
    "ts_delta", "ts_zscore", "ts_sum", "ts_std_dev", "ts_mean",
    "ts_corr", "ts_covariance", "ts_decay_linear", "ts_product",
    "ts_regression", "ts_step", "ts_rank", "ts_scale", "ts_quantile",
    "ts_delay", "ts_backfill", "ts_count_nans",
    "ts_arg_max", "ts_arg_min", "ts_av_diff",
    # Misc
    "kth_element", "days_from_last_change", "hump", "last_diff_value",
    "trade_when", "vec_sum", "vec_avg",
}
# fmt: on

SKIP_TOKENS = VALID_OPS | {
    "sector",
    "industry",
    "subindustry",
    "market",
    "true",
    "false",
    "filter",
    "dense",
    "lag",
    "range",
    "lookback",
    "rettype",
    "driver",
    "gaussian",
    "std",
    "constant",
    "skipboth",
    "nangroup",
}
