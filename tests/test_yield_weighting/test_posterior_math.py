"""yield_weight() posterior-mean math: prior, high yield, low yield, ratio."""

from generator.diversity_weights import (
    YIELD_PRIOR_ALPHA,
    YIELD_PRIOR_BETA,
    YIELD_PRIOR_MEAN,
    yield_weight,
)


def test_yield_weight_no_data_equals_prior_mean():
    """A config with no observations gets the prior mean (alpha / (alpha+beta))."""
    expected = YIELD_PRIOR_ALPHA / (YIELD_PRIOR_ALPHA + YIELD_PRIOR_BETA)
    assert yield_weight(winners=0, count=0) == expected
    assert expected == YIELD_PRIOR_MEAN


def test_yield_weight_high_yield_above_prior():
    """A high-hit config (12 winners / 100 sims) lands above the 2% prior."""
    w = yield_weight(winners=12, count=100)
    assert w > YIELD_PRIOR_MEAN
    # Posterior mean: (1 + 12) / (50 + 100) = 13/150 ≈ 0.087.
    assert abs(w - 13 / 150) < 1e-9


def test_yield_weight_low_yield_below_prior():
    """A no-hit config with many sims should fall below the prior."""
    w = yield_weight(winners=0, count=200)
    # (1 + 0) / (50 + 200) = 1/250 = 0.004.
    assert w < YIELD_PRIOR_MEAN
    assert abs(w - 1 / 250) < 1e-9


def test_yield_weight_dominates_count_for_high_yield():
    """The whole point of F2: a high-yield config (IND-like) gets more weight
    under yield mode than under count mode, even with smaller sample size."""
    # IND-like: 432 sims, 52 winners (~12%).
    ind_yield = yield_weight(winners=52, count=432)
    ind_count = 1.0 / (1.0 + 432)
    # USA-like: 1983 sims, 36 winners (~1.8%).
    usa_yield = yield_weight(winners=36, count=1983)
    usa_count = 1.0 / (1.0 + 1983)

    # Under count mode: IND/USA weight ratio ~ 4.6x.
    # Under yield mode: ratio is much larger.
    assert ind_yield / usa_yield > ind_count / usa_count
