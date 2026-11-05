"""The HKG single-interval backfill: predicate, region gate, dispatch seam."""

import random

import pytest

from generator.field_picker import FieldCache, set_cache
from generator.random_generator_dispatch import _call_template
from generator.templates_brain_website_pick import _maybe_backfill, _pick
from generator.templates_cnhkmcp_canonical import quantile_ts_rank


@pytest.fixture
def cache():
    set_cache(FieldCache())
    yield
    set_cache(FieldCache())


def _load(region):
    c = FieldCache()
    c.last_loaded = (region, 1, "TOP800")
    set_cache(c)


def test_the_predicate_targets_single_interval_pv37_fields(cache):
    _load("HKG")
    assert _maybe_backfill("pv37_close_12") == "ts_backfill(pv37_close_12, 63)"
    assert _maybe_backfill("pv37_volume_1430") == "ts_backfill(pv37_volume_1430, 63)"
    # Session aggregates and the other families are untouched — the 2026-10-15
    # measurement has them on the passing side of the split.
    for field in (
        "session_1430to1430_total_traded_volume",
        "pv37_profitabil_cons_di",
        "pv141_volume_ratio_wq_w_close_market",
        "pv37_s_dq_preclose",
        "",
        None,
    ):
        assert _maybe_backfill(field) == field


def test_the_gate_is_the_loaded_region(cache):
    # Other regions stay byte-identical — this is what keeps the wrap from
    # contaminating the other regions' emissions or their in-flight reads.
    for region in ("USA", "CHN", "KOR"):
        _load(region)
        assert _maybe_backfill("pv37_close_12") == "pv37_close_12"
    set_cache(FieldCache())  # unloaded pool: also untouched
    assert _maybe_backfill("pv37_close_12") == "pv37_close_12"


def test_a_pick_in_hkg_wraps_and_elsewhere_does_not(cache):
    _load("HKG")
    assert _pick(["pv37_close_12"], random.Random(0), "close") == "ts_backfill(pv37_close_12, 63)"
    _load("USA")
    assert _pick(["pv37_close_12"], random.Random(0), "close") == "pv37_close_12"


def test_the_two_field_dispatch_wraps(cache):
    # `quantile_ts_rank(pv37_high_12, 250)` is one of the measured
    # CONCENTRATED_WEIGHT failures; its field arrives through this call.
    _load("HKG")
    expr = _call_template(quantile_ts_rank, ["pv37_high_12", "pv20_returns15_1001"])
    assert "ts_backfill(pv37_high_12, 63)" in expr

    _load("USA")
    expr = _call_template(quantile_ts_rank, ["pv37_high_12", "pv20_returns15_1001"])
    assert "ts_backfill(pv37_high_12, 63)" not in expr
