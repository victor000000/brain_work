"""Role contracts and real parser checks for finite cost-aware experiments."""

import random

import pytest

from generator.idea_templates_liquidity import (
    COST_FIELD,
    LIQUIDITY_CONTROL_TEMPLATES,
    LIQUIDITY_IDEA_TEMPLATES,
)
from generator.template_fill import filled_expression_problem


@pytest.mark.parametrize("fn", LIQUIDITY_IDEA_TEMPLATES + LIQUIDITY_CONTROL_TEMPLATES)
def test_missing_price_roles_never_fall_back_to_an_unrelated_field(fn):
    assert fn([COST_FIELD, "open", "opt6_slcxp"], random.Random(1)) is None
    assert fn(["close", COST_FIELD, "pv87_vwap_estimate"], random.Random(1)) is None


@pytest.mark.parametrize("fn", LIQUIDITY_IDEA_TEMPLATES + LIQUIDITY_CONTROL_TEMPLATES[:1])
def test_cost_roles_require_the_verified_field_not_a_name_match(fn):
    assert fn(["close", "vwap", "cost_percentile_label", "option_transaction_cost"], random.Random(1)) is None


@pytest.mark.parametrize("fn", LIQUIDITY_IDEA_TEMPLATES + LIQUIDITY_CONTROL_TEMPLATES)
def test_direct_and_smoothed_variants_pass_real_expression_validation(fn):
    fields = ["close", "vwap", COST_FIELD]
    expression = fn(fields, random.Random(1))
    for candidate in [expression, f"ts_decay_linear({expression}, 5)"]:
        assert filled_expression_problem(candidate, fields, {"rank", "ts_decay_linear"}, (), ()) is None
