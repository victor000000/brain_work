"""A 16:00 close and a 14:30 VWAP are not one contemporaneous pair."""

import random

import pytest

from generator.field_picker.cache import FieldCache, set_cache
from generator.templates_brain_website_price_action import vwap_close_spread


@pytest.fixture(autouse=True)
def isolated_cache():
    set_cache(FieldCache())
    yield
    set_cache(FieldCache())


@pytest.mark.parametrize("cached", [False, True])
def test_recorded_mixed_window_pair_is_not_emitted(cached):
    fields = ["pv98_close_16", "pv98_vwap_1430"]
    if cached:
        cache = FieldCache()
        cache.matrix_by_dataset = {"pv98": fields}
        set_cache(cache)
    for seed in range(20):
        assert vwap_close_spread(fields, random.Random(seed)) is None


@pytest.mark.parametrize(
    "fields",
    [
        ["pv98_close_16_backfill", "pv98_vwap_16"],
        ["pv98_close_16", "pv37_vwap_16"],
        ["pv98_close_16", "pv98_vwap_price_ratio_16"],
        ["vwap_30m_pre_close"],
    ],
)
def test_different_contexts_and_derived_features_do_not_match(fields):
    assert vwap_close_spread(fields, random.Random(4)) is None


def test_matching_families_preserve_diversity():
    fields = [
        "close",
        "vwap",
        "pv98_close_16",
        "pv98_vwap_16",
        "pv98_close_1430_backfill",
        "pv98_vwap_1430_backfill",
        "pv98_vwap_10",
    ]
    expected = {
        "(close - vwap) / vwap",
        "(pv98_close_16 - pv98_vwap_16) / pv98_vwap_16",
        "(pv98_close_1430_backfill - pv98_vwap_1430_backfill) / pv98_vwap_1430_backfill",
    }
    assert {vwap_close_spread(fields, random.Random(seed)) for seed in range(100)} == expected


def test_cache_cannot_supply_an_unoffered_companion():
    cache = FieldCache()
    cache.matrix_by_dataset = {"pv98": ["pv98_close_16", "pv98_vwap_16"]}
    set_cache(cache)
    assert vwap_close_spread(["pv98_close_16", "pv98_vwap_1430"], random.Random(2)) is None


def test_backfill_policy_applies_after_matching():
    cache = FieldCache()
    cache.last_loaded = ("HKG", 1, "TOP800")
    set_cache(cache)
    assert (
        vwap_close_spread(["pv37_close_16", "pv37_vwap_16"], random.Random(1))
        == "(ts_backfill(pv37_close_16, 63) - ts_backfill(pv37_vwap_16, 63)) / ts_backfill(pv37_vwap_16, 63)"
    )
