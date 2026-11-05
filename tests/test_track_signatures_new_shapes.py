"""The 2026-10-12/13 shapes keep their labels when generation tracking misses.

`identify_template` prefers the in-memory generation-time map; a reattached
batch stored by a later process has no entry there and falls to the regex
signature list, which before these entries spoke only the legacy vocabulary —
so a `dual_bucket_neutralized` alpha could be recorded as `peer_rank` or
`unknown`, misattributing exactly the shapes whose records are being read.
"""

import pytest

from storage.track_templates import identify_template

CASES = [
    ("rank(ts_delta(pv98_close, 43))", None),  # control: legacy fallback, unchanged
    ("ts_target_tvr_decay(rank(some_field / ts_delay(some_field, 1) - 1), target_tvr=0.1)", "tvr_targeted_turnover"),
    ("group_neutralize(group_zscore(sig, sector), group_cartesian_product(b1, b2))", "dual_bucket_neutralized"),
    ("tail(group_zscore(close, sector), lower=-1.1, upper=1.1, newval=0)", "tail_extreme_signal"),
    ("trade_when(and(volume > ts_mean(volume, 20), rank(x) > 0.5), y, -1)", "double_gated_momentum"),
    ("trade_when(greater(ts_rank(x, 252), 0.3), y, nan)", "quality_gated_value"),
    ("ts_covariance(rank(close), rank(volume), 60)", "covariance_divergence"),
    ("hump(rank(close / ts_delay(close, 1) - 1), hump=0.05)", "hump_turnover_controlled"),
    ("ts_ir(returns, 120)", "ts_ir_trend"),
    ("rank(ts_decay_linear(ts_zscore(ts_backfill(ivc, 22) - ts_backfill(ivp, 22), 504), 5))", "iv_skew_reversal"),
    ("rank(ts_zscore(returns, 250))", "long_window_normalized"),
]


@pytest.mark.parametrize(("expression", "expected"), CASES)
def test_new_shape_signatures(expression, expected):
    if expected is None:
        assert identify_template(expression) != "long_window_normalized"
        return
    assert identify_template(expression) == expected
