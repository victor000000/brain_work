"""Idea probes use real price/volume roles and the production validator."""

import random

import pytest

from generator.idea_templates import IDEA_TEMPLATES
from generator.template_fill import filled_expression_problem

OPERATORS = {"rank", "ts_corr", "ts_delta", "ts_delay", "ts_mean", "ts_backfill"}


@pytest.mark.parametrize("template", IDEA_TEMPLATES)
def test_ideas_validate_for_canonical_and_interval_fields(template):
    for fields in (("close", "volume"), ("pv37_close_12", "pv37_volume_1430")):
        for seed in range(30):
            expression = template(fields, random.Random(seed))
            assert expression is not None
            assert filled_expression_problem(expression, fields, OPERATORS, set(), set()) is None


@pytest.mark.parametrize("template", IDEA_TEMPLATES)
@pytest.mark.parametrize("fields", [(), ("close",), ("volume",), ("close", "pv141_volume_ratio_wq_w_close_market")])
def test_ideas_require_both_a_price_and_raw_volume(template, fields):
    assert template(fields, random.Random(0)) is None
