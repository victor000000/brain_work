"""Displacement probes keep daily price roles and pass production validation."""

import ast
import random

import pytest

from generator.idea_templates_displacement import (
    DISPLACEMENT_CONTROL_TEMPLATES,
    DISPLACEMENT_IDEA_TEMPLATES,
    anchored_close_vwap_quantile,
    anchored_price_quantile,
    close_vwap_displacement_only,
    close_vwap_quantile_only,
    price_displacement_only,
    price_quantile_only,
)
from generator.template_fill import filled_expression_problem

OPERATORS = {"rank", "ts_quantile", "ts_av_diff"}
ALL_PROBES = DISPLACEMENT_IDEA_TEMPLATES + DISPLACEMENT_CONTROL_TEMPLATES


@pytest.mark.parametrize("template", ALL_PROBES)
def test_fixed_shape_and_inverse_pass_production_validator(template):
    expression = template({"close", "vwap", "volume"}, random.Random(0))
    for oriented in (expression, f"-({expression})"):
        assert filled_expression_problem(oriented, {"close", "vwap", "volume"}, OPERATORS, set(), set()) is None


@pytest.mark.parametrize("template", ALL_PROBES)
@pytest.mark.parametrize("fields", [set(), {"volume"}, {"open_interest"}, {"implied_volatility_call_30", "vwap"}])
def test_no_unrelated_fallback_when_daily_close_is_missing(template, fields):
    assert template(fields, random.Random(0)) is None


@pytest.mark.parametrize(
    "relative,nominal",
    [
        (anchored_close_vwap_quantile, anchored_price_quantile),
        (close_vwap_displacement_only, price_displacement_only),
        (close_vwap_quantile_only, price_quantile_only),
    ],
)
def test_relative_displacement_requires_both_daily_prices(relative, nominal):
    assert relative({"close", "pv37_vwap_163000"}, random.Random(0)) is None
    assert nominal({"close"}, random.Random(0)) is not None


@pytest.mark.parametrize(
    "combined,displacement,quantile",
    [
        (anchored_price_quantile, price_displacement_only, price_quantile_only),
        (anchored_close_vwap_quantile, close_vwap_displacement_only, close_vwap_quantile_only),
    ],
)
def test_controls_drop_one_transform_and_preserve_source_and_windows(combined, displacement, quantile):
    def inner(template):
        expression = template({"close", "vwap"}, random.Random(0))
        return ast.parse(expression, mode="eval").body.args[0]

    stacked, centered, historical = inner(combined), inner(displacement), inner(quantile)
    assert stacked.func.id == historical.func.id == "ts_quantile"
    assert centered.func.id == "ts_av_diff"
    assert ast.dump(stacked.args[0]) == ast.dump(centered)
    assert ast.dump(stacked.args[1]) == ast.dump(historical.args[1])
    assert ast.dump(centered.args[0]) == ast.dump(historical.args[0])


@pytest.mark.parametrize("template", DISPLACEMENT_IDEA_TEMPLATES)
def test_operator_allowlist_still_applies(template):
    expression = template({"close", "vwap"}, random.Random(0))
    assert filled_expression_problem(expression, {"close", "vwap"}, OPERATORS - {"ts_quantile"}, set(), set()) == (
        "unknown operator(s): ts_quantile"
    )
