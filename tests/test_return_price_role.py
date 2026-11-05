"""Price-derived stock returns cannot use a modulo-price ratio as close."""

import random

import pytest

from generator.field_picker.cache import FieldCache, set_cache
from generator.templates_brain_website_group_cap import dual_bucket_neutralized
from generator.templates_brain_website_momentum import return_mean_20d, return_mean_reversion
from generator.templates_brain_website_reversion import return_vol_20d, return_volatility
from generator.templates_brain_website_transform import (
    hump_turnover_controlled,
    tvr_targeted_turnover,
    winsorized_signal,
)
from generator.validate import parse_error

BAD = "mean_price_modulo_1_ratio_30m_pre_close"
TEMPLATES = [
    hump_turnover_controlled,
    tvr_targeted_turnover,
    return_mean_reversion,
    return_mean_20d,
    return_volatility,
    return_vol_20d,
    dual_bucket_neutralized,
]
OPS = {
    "hump",
    "ts_target_tvr_decay",
    "rank",
    "ts_delay",
    "ts_mean",
    "ts_std_dev",
    "group_neutralize",
    "group_zscore",
    "group_cartesian_product",
    "bucket",
    "ts_backfill",
}


@pytest.fixture(autouse=True)
def isolated_cache():
    set_cache(FieldCache())
    yield
    set_cache(FieldCache())


@pytest.mark.parametrize("template", TEMPLATES)
def test_modulo_ratio_cannot_supply_a_stock_return_price(template):
    assert template([BAD], random.Random(7)) is None


@pytest.mark.parametrize("template", TEMPLATES)
@pytest.mark.parametrize("price", ["close", "pv37_close_1430", "last_trade_price_30m_pre_close_2"])
def test_return_templates_keep_raw_prices_amid_modulo_decoys(template, price):
    for seed in range(10):
        code = template([BAD, "price_close_ratio", price], random.Random(seed))
        assert code is not None
        assert BAD not in code and "price_close_ratio" not in code
        assert price in code
        assert parse_error(code, OPS) is None


def test_modulo_feature_remains_available_to_an_any_field_transform():
    assert BAD in winsorized_signal([BAD], random.Random(7))


@pytest.mark.parametrize("template", [hump_turnover_controlled, tvr_targeted_turnover])
def test_hkg_backfill_and_named_turnover_parameters_survive(template):
    cache = FieldCache()
    cache.last_loaded = ("HKG", 1, "TOP800")
    set_cache(cache)
    code = template([BAD, "pv37_close_1430"], random.Random(7))
    assert code is not None
    assert "ts_backfill(pv37_close_1430, 63)" in code
    assert ("hump=" in code) if template is hump_turnover_controlled else ("target_tvr=" in code)
    assert parse_error(code, OPS) is None
