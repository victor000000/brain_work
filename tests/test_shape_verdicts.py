"""Decision boundaries come from the recorded rules, without post-hoc tuning."""

import pytest

from tools.shape_verdicts import SHAPE_THRESHOLDS, shape_verdict


def _stats(n, median=0.2, hits=10):
    return {"sharpes": [median] * n, "at_floor": hits}


@pytest.mark.parametrize("name", SHAPE_THRESHOLDS)
def test_no_shape_gets_a_verdict_before_its_threshold(name):
    n = SHAPE_THRESHOLDS[name] - 1
    decision, reason = shape_verdict(name, _stats(n), _stats(1000))
    assert decision == "WAIT"
    assert "1 more needed" in reason


@pytest.mark.parametrize("hits,decision", [(4, "KEEP"), (3, "INCONCLUSIVE"), (2, "RETIRE")])
def test_long_window_uses_floor_rate_at_two_times_one_time_and_between(hits, decision):
    assert shape_verdict("long_window_normalized", _stats(100, hits=hits), _stats(1000, hits=20))[0] == decision


def test_zero_population_floor_rate_cannot_manufacture_a_keep():
    assert shape_verdict("long_window_normalized", _stats(100, hits=1), _stats(1000, hits=0))[0] == "INCONCLUSIVE"


@pytest.mark.parametrize(
    "name,median,decision",
    [
        ("dual_bucket_neutralized", 0.1, "KEEP"),
        ("dual_bucket_neutralized", 0.0, "RETIRE"),
        ("dual_bucket_neutralized", 0.05, "INCONCLUSIVE"),
        ("quality_gated_value", 0.3, "KEEP"),
        ("quality_gated_value", 0.25, "INCONCLUSIVE"),
        ("hump_turnover_controlled", 0.2, "RETIRE"),
        ("tail_extreme_signal", 0.25, "KEEP"),
        ("iv_skew_reversal", 0.05, "RETIRE"),
        ("covariance_divergence", 0.2, "INCONCLUSIVE"),
    ],
)
def test_median_decisions_honor_the_registered_gaps(name, median, decision):
    n = SHAPE_THRESHOLDS[name]
    assert shape_verdict(name, _stats(n, median), _stats(1000))[0] == decision


def test_dual_bucket_zero_hits_retire_rule_takes_precedence_over_keep():
    assert shape_verdict("dual_bucket_neutralized", _stats(250, hits=0), _stats(1000, hits=8))[0] == "RETIRE"


def test_missing_population_is_inconclusive():
    assert shape_verdict("long_window_normalized", _stats(100), _stats(0, hits=0))[0] == "INCONCLUSIVE"
