"""A volume-weighted average price cannot supply a traded-volume role."""

import random

import pytest

from generator.field_picker.cache import FieldCache, set_cache
from generator.templates_brain_website_pick import _RAW_VOLUME_EXCLUDE, _pick_tokens
from generator.templates_brain_website_volume import (
    covariance_divergence,
    double_gated_momentum,
    options_pcr_volume_gated,
    quality_gated_value,
    volume_gated_momentum,
    volume_surge,
)

VWAP = "session_1430to1430_volume_weighted_avg_price"


@pytest.fixture(autouse=True)
def isolated_cache():
    set_cache(FieldCache())
    yield
    set_cache(FieldCache())


@pytest.mark.parametrize(
    "template",
    [
        volume_surge,
        volume_gated_momentum,
        options_pcr_volume_gated,
        covariance_divergence,
        double_gated_momentum,
        quality_gated_value,
    ],
)
def test_price_only_pool_cannot_create_a_volume_gate(template):
    # All other required roles are offered; only genuine volume is absent.
    fields = [VWAP, "close", "vwap", "pcr_oi_180"]
    assert template(fields, random.Random(7)) is None


@pytest.mark.parametrize("volume", ["volume", "pv37_volume_1430", "min_trade_volume_30m_pre_close_2"])
def test_native_volume_roles_remain_available_amid_price_and_ratio_decoys(volume):
    fields = [VWAP, "volume_vwap", "volume_ratio", "average_volume", volume]
    for seed in range(20):
        assert _pick_tokens(fields, random.Random(seed), ("volume",), _RAW_VOLUME_EXCLUDE) == volume


def test_gated_price_fallback_uses_real_volume_without_changing_its_signal():
    expression = options_pcr_volume_gated([VWAP, "volume", "close"], random.Random(2))
    assert expression is not None
    assert "rank(volume / ts_mean(volume," in expression
    assert "ts_delta(close, 20)" in expression
    assert VWAP not in expression


def test_hkg_volume_backfill_remains_applied_after_role_selection():
    cache = FieldCache()
    cache.last_loaded = ("HKG", 1, "TOP800")
    set_cache(cache)
    assert _pick_tokens([VWAP, "pv37_volume_1430"], random.Random(1), ("volume",), _RAW_VOLUME_EXCLUDE) == (
        "ts_backfill(pv37_volume_1430, 63)"
    )
