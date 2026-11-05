"""Top-performing cnhkmcp templates — top 20% by IS sharpe.

Kept (avg IS sharpe across all variants):
  power_ratio         -0.03  best tracked performer
  staleness_decay     -0.07  staleness_decay+3f_mean is +0.08
  scale_rank_zscore   -0.08  consistent cross-sectional
  raw_regression_long -0.10  generates +0.76 raw_regression pattern
  raw_regression_med  -0.09  same pattern, medium windows

Removed 17 templates averaging -0.11 to -0.23 IS sharpe.

Plus 5 canonical patterns ported from cnhkmcp 3.1.11 KB (no perf data yet —
diversity weighting will surface or suppress them as observations accumulate).
"""

from generator.templates_cnhkmcp_advanced import scale_rank_zscore
from generator.templates_cnhkmcp_canonical import (
    group_rank_diff,
    quantile_ts_rank,
    trade_when_event,
    ts_backfill_negmean,
    ts_corr_long,
)
from generator.templates_cnhkmcp_highperf import (
    power_ratio,
    raw_regression_long,
    raw_regression_medium,
)
from generator.templates_cnhkmcp_vec import staleness_decay

TEMPLATES_CNHKMCP = [
    (power_ratio, ["rank", "signed_power", "ts_mean", "abs"]),
    (raw_regression_long, ["rank", "ts_regression"]),
    (raw_regression_medium, ["rank", "ts_regression"]),
    (staleness_decay, ["rank", "days_from_last_change"]),
    (scale_rank_zscore, ["rank", "scale", "ts_zscore"]),
    # cnhkmcp 3.1.11 canonical patterns (exploration)
    (quantile_ts_rank, ["quantile", "ts_rank"]),
    (group_rank_diff, ["group_rank"]),
    (ts_corr_long, ["ts_corr", "ts_backfill"]),
    (trade_when_event, ["trade_when", "days_from_last_change", "rank"]),
    (ts_backfill_negmean, ["ts_mean", "ts_backfill"]),
]
