"""A ten-day high and a 14:30 low are not one measured price range."""

import random

import pytest

from generator.field_picker.cache import FieldCache, set_cache
from generator.templates_brain_website_price_action import high_low_spread


@pytest.fixture(autouse=True)
def isolated_cache():
    set_cache(FieldCache())
    yield
    set_cache(FieldCache())


@pytest.mark.parametrize("cached", [False, True])
def test_recorded_cross_window_range_is_not_emitted(cached):
    fields = ["pv37_high_10", "pv37_low_1430", "pv37_close_1430"]
    if cached:
        cache = FieldCache()
        cache.matrix_by_dataset = {"pv37": fields}
        set_cache(cache)
    for seed in range(20):
        assert high_low_spread(fields, random.Random(seed)) is None


def test_daily_and_intraday_families_stay_complete_across_draws():
    fields = [
        "pv37_high_10",
        "pv37_low_10",
        "pv37_close_10",
        "pv37_high_1430",
        "pv37_low_1430",
        "pv37_close_1430",
        "pv37_high_140000",
    ]
    expected = {
        "(pv37_high_10 - pv37_low_10) / pv37_close_10",
        "(pv37_high_1430 - pv37_low_1430) / pv37_close_1430",
    }
    observed = {high_low_spread(fields, random.Random(seed)) for seed in range(100)}
    assert observed == expected


def test_only_offered_fields_can_complete_the_range():
    cache = FieldCache()
    cache.matrix_by_dataset = {"pv37": ["pv37_high_10", "pv37_low_10", "pv37_close_10"]}
    set_cache(cache)
    assert high_low_spread(["pv37_high_10", "pv37_low_1430", "pv37_close_1430"], random.Random(2)) is None


def test_canonical_daily_prices_still_generate_a_range():
    assert high_low_spread(["high", "low", "close"], random.Random(2)) == "(high - low) / close"


def test_mixed_datasets_and_derived_price_roles_cannot_complete_a_range():
    fields = ["pv37_high_10", "pv98_low_10", "pv37_close_10", "pv37_low_price_ratio_10", "high_low_price"]
    assert high_low_spread(fields, random.Random(4)) is None


def test_existing_hkg_backfill_policy_is_applied_after_matching():
    cache = FieldCache()
    cache.last_loaded = ("HKG", 1, "TOP800")
    set_cache(cache)
    fields = ["pv37_high_1430", "pv37_low_1430", "pv37_close_1430"]
    assert high_low_spread(fields, random.Random(6)) == (
        "(ts_backfill(pv37_high_1430, 63) - ts_backfill(pv37_low_1430, 63)) / ts_backfill(pv37_close_1430, 63)"
    )
