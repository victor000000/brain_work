"""generate_from_templates: only validated, field-bearing expressions."""

import random

from generator.template_fill import generate_from_templates, unknown_field_tokens
from tests.test_template_fill_helpers import FIELDS


def test_generate_from_templates_never_emits_a_fieldless_constant():
    templates = [{"skeleton": "ts_av_diff(185,5)"}, {"skeleton": "ts_rank({f},20)"}]
    out = generate_from_templates(templates, FIELDS, count=10, rng=random.Random(3))
    assert out
    for expr in out:
        assert unknown_field_tokens(expr, FIELDS) == set(), expr
        assert any(f in expr for f in FIELDS), expr


def test_generate_returns_valid_expressions_only():
    templates = [{"skeleton": "ts_rank({f},20)"}, {"skeleton": "rank({f})"}]
    out = generate_from_templates(templates, FIELDS, count=5, rng=random.Random(3))
    assert len(out) == 5
    from generator.validate import parse_error

    for expr in out:
        assert parse_error(expr) is None, expr


def test_generate_drops_templates_that_cannot_validate():
    templates = [{"skeleton": "rank({f})"}, {"skeleton": "rank({f}"}]  # second is unbalanced
    out = generate_from_templates(templates, FIELDS, count=6, rng=random.Random(5))
    assert out
    for expr in out:
        assert expr.count("(") == expr.count(")")


def test_generate_returns_empty_when_no_templates_survive():
    out = generate_from_templates([{"skeleton": "rank({f"}], FIELDS, count=5, rng=random.Random(1))
    assert out == []
