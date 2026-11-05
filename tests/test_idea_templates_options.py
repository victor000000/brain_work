"""Option probes preserve dataset, maturity, side and production validation."""

import random

import pytest

from generator.idea_templates_options import (
    _IV_FAMILIES,
    _SKEW_TENORS,
    _TERM_TENORS,
    OPTIONS_IDEA_TEMPLATES,
    _iv_skew_pairs,
    _iv_term_pairs,
    iv_put_term_stress,
    iv_relative_skew_reversal,
)
from generator.template_fill import filled_expression_problem

OPERATORS = {"rank", "ts_decay_linear", "ts_zscore"}


@pytest.mark.parametrize("call,put", _IV_FAMILIES)
def test_skew_pairs_are_same_dataset_same_tenor(call, put):
    fields = [pattern.format(tenor) for pattern in (call, put) for tenor in _SKEW_TENORS]
    assert _iv_skew_pairs(fields) == [(call.format(t), put.format(t)) for t in _SKEW_TENORS]
    for seed in range(40):
        expression = iv_relative_skew_reversal(fields, random.Random(seed))
        assert expression is not None
        assert filled_expression_problem(expression, fields, OPERATORS, set(), set()) is None


@pytest.mark.parametrize("call,put", _IV_FAMILIES)
def test_term_pairs_are_same_dataset_puts_in_near_far_order(call, put):
    fields = [put.format(tenor) for tenor in _SKEW_TENORS]
    assert _iv_term_pairs(fields) == [(put.format(near), put.format(far)) for near, far in _TERM_TENORS]
    assert all(near < far for near, far in _TERM_TENORS)
    for seed in range(40):
        expression = iv_put_term_stress(fields, random.Random(seed))
        assert expression is not None
        assert filled_expression_problem(expression, fields, OPERATORS, set(), set()) is None


@pytest.mark.parametrize("template", OPTIONS_IDEA_TEMPLATES)
@pytest.mark.parametrize(
    "fields",
    [
        (),
        ("close", "volume"),
        ("historical_volatility_30", "historical_volatility_90"),
        ("opt40_call_volatility_30days", "put_option_implied_volatility_30d"),
        ("call_option_volatility_exposure_30d", "put_option_volatility_exposure_91d"),
        ("opt40_ivcall30", "implied_volatility_put_30"),  # different datasets
        ("implied_volatility_put_30", "opt40_ivput90"),  # different datasets
        ("implied_volatility_call_30", "implied_volatility_put_90"),  # different roles
        ("implied_volatility_mean_skew_30", "implied_volatility_mean_30"),
        ("implied_volatility_call_31", "implied_volatility_put_31"),  # unverified tenor
    ],
)
def test_no_arbitrary_field_pair_or_unrelated_fallback(template, fields):
    assert template(fields, random.Random(0)) is None


def test_skew_normalizes_exact_same_tenor_ivs_and_preserves_direction():
    fields = ("implied_volatility_call_30", "implied_volatility_put_30")
    assert iv_relative_skew_reversal(fields, random.Random(0)) == (
        "-rank(ts_decay_linear(ts_zscore((implied_volatility_put_30 - implied_volatility_call_30) / "
        "(implied_volatility_put_30 + implied_volatility_call_30), 126), 5))"
    )


def test_term_stress_uses_annualized_iv_directly_without_tenor_rescaling():
    fields = ("opt40_ivput30", "opt40_ivput90")
    assert iv_put_term_stress(fields, random.Random(0)) == (
        "-rank(ts_decay_linear(ts_zscore(opt40_ivput30 / opt40_ivput90, 126), 5))"
    )


@pytest.mark.parametrize("template", OPTIONS_IDEA_TEMPLATES)
def test_missing_option_operator_is_rejected_by_production_validator(template):
    fields = ("opt40_ivcall30", "opt40_ivput30", "opt40_ivput90")
    expression = template(fields, random.Random(0))
    assert (
        filled_expression_problem(expression, fields, OPERATORS - {"ts_zscore"}, set(), set())
        == "unknown operator(s): ts_zscore"
    )


@pytest.mark.parametrize("template", OPTIONS_IDEA_TEMPLATES)
def test_production_validator_rejects_operand_not_in_matrix_pool(template):
    fields = ("opt40_ivcall30", "opt40_ivput30", "opt40_ivput90")
    expression = template(fields, random.Random(0))
    assert (
        filled_expression_problem(expression, set(fields) - {"opt40_ivput30"}, OPERATORS, set(), set())
        == "unknown field(s): opt40_ivput30"
    )
