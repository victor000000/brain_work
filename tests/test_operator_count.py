"""Prevent the observed native 66-operation rejection before probe dispatch."""

import pytest

from generator.operator_count import operator_count
from runner import probe_validation
from runner.settings_factory import make_settings


def test_constants_groups_and_variable_reuse():
    assert operator_count("rank((-1 * close) + (-0.5))") == 3
    assert operator_count("x = rank(close); x + x + x") == 3
    assert operator_count("rank(close) + rank(close) + rank(close)") == 5
    assert operator_count("close > 0 ? -close : volume") == 3


def test_native_rejected_and_factored_regression():
    momentum = "rank(ts_delay(if_else(ts_count_nans(if_else(returns > -1, returns, nan),231) == 0, (ts_product(1 + if_else(returns > -1, returns, nan),231) - 1), nan),21))"
    daily = "if_else((volume >= 0) && (sharesout > 0), volume / (sharesout * 1000000), nan)"
    liquidity = f"ts_delay(if_else(ts_count_nans({daily},21) == 0, ts_mean({daily},21), nan),21)"
    expanded = (
        f"rank(if_else((is_nan({momentum}) || is_nan({liquidity})), nan, ({momentum} - 0.5) * rank({liquidity})))"
    )
    factored = f"m={momentum};l={liquidity};rank(if_else(is_nan(m)||is_nan(l),nan,(m-0.5)*rank(l)))"
    assert operator_count(expanded) == 66
    assert operator_count(factored) == 37


def test_probe_enforces_boundary_before_field_expansion(monkeypatch):
    monkeypatch.setattr(probe_validation, "target_pools", lambda *a: ({"close"}, set(), set()))
    monkeypatch.setattr(probe_validation, "load_operator_names", lambda *a: {"rank"})
    settings = make_settings("USA", "TOP3000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    valid = "+".join(["rank(close)"] * 32) + "+close"
    assert operator_count(valid) == 64
    probe_validation.validate_probe(None, [valid], settings, ["test"])
    with pytest.raises(ValueError, match="65 operators"):
        probe_validation.validate_probe(None, [valid + "+close"], settings, ["test"])
