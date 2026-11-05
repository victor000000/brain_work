"""The ten shape decisions frozen in TODO.md on 2026-10-13."""

import math
import statistics

SHAPE_THRESHOLDS = {
    "long_window_normalized": 100,
    "iv_skew_reversal": 60,
    "tail_extreme_signal": 250,
    "quality_gated_value": 250,
    "ts_ir_trend": 250,
    "tvr_targeted_turnover": 250,
    "hump_turnover_controlled": 250,
    "double_gated_momentum": 250,
    "covariance_divergence": 250,
    "dual_bucket_neutralized": 250,
}


def shape_verdict(name, row, population):
    """Return (decision, reason) without changing registration or weights.

    Missing measurements cannot supply statistical power. The population is
    the same labelled-alpha window for every shape; IV's own sample is USA-only.
    """
    threshold = SHAPE_THRESHOLDS[name]
    n = len(row["sharpes"]) if row else 0
    if n < threshold:
        return "WAIT", f"{n}/{threshold} measured; {threshold - n} more needed"
    if not population["sharpes"]:
        return "INCONCLUSIVE", "population has no measured Sharpe"
    median = statistics.median(row["sharpes"])
    baseline = statistics.median(population["sharpes"])
    delta = median - baseline
    rate = row["at_floor"] / n
    population_rate = population["at_floor"] / len(population["sharpes"])
    if name == "long_window_normalized":
        detail = f"floor {rate:.2%} vs population {population_rate:.2%}"
        if population_rate == 0:
            return "INCONCLUSIVE", detail + "; zero baseline"
        if rate >= 2 * population_rate:
            return "KEEP", detail
        if rate <= population_rate:
            return "RETIRE", detail
        return "INCONCLUSIVE", detail + "; between 1x and 2x"
    detail = f"median gap {delta:+.3f}"
    if name == "dual_bucket_neutralized":
        expected = n * population_rate
        if delta <= -0.20 or math.isclose(delta, -0.20, abs_tol=1e-12):
            return "RETIRE", detail
        if row["at_floor"] == 0 and expected >= 2:
            return "RETIRE", f"0 floor hits vs {expected:.2f} expected"
        if abs(delta) <= 0.10 or math.isclose(abs(delta), 0.10, abs_tol=1e-12):
            return "KEEP", detail
        return "INCONCLUSIVE", detail
    keep_gap, retire_gap = (0.10, 0) if name in {"hump_turnover_controlled", "quality_gated_value"} else (0.05, -0.15)
    if delta >= keep_gap or math.isclose(delta, keep_gap, abs_tol=1e-12):
        return "KEEP", detail
    if delta <= retire_gap or math.isclose(delta, retire_gap, abs_tol=1e-12):
        return "RETIRE", detail
    return "INCONCLUSIVE", detail
