"""Template expressions: pool fills, field use and keyword degradation."""

import random

from generator.registry import ALL_TEMPLATES, template_uses_pool
from tests.test_templates_helpers import ANY_FIELD, POOL, _call


def test_templates_generate_expressions():
    """Each template produces a non-empty string with balanced parens."""
    for fn, _ops in ALL_TEMPLATES:
        expr = _call(fn)
        assert isinstance(expr, str), f"{fn.__name__} returned {type(expr)}"
        assert len(expr) > 10, f"{fn.__name__} too short: {expr}"
        assert expr.count("(") == expr.count(")"), f"{fn.__name__} unbalanced parens: {expr}"


def test_pool_templates_use_a_pool_field():
    """A pool-based template's expression reads a field it picked from the pool."""
    for fn, _ops in ALL_TEMPLATES:
        if not template_uses_pool(fn):
            continue
        expr = _call(fn)
        assert any(field in expr for field in POOL), f"{fn.__name__} picks no pool field: {expr}"


def test_group_templates_pass_a_real_group():
    """A `group_*` operator's group argument is a grouping, not a datafield.

    Sourcing it with a keyword search over the pool matched `pv20_sector_1964`
    (a MATRIX whose *name* contains "sector"), and the platform rejects the
    simulation with `expected "Unit[Group:1]", found "Unit[]"` — one budget
    slot each. Seen live on 2026-10-06 against HKG's pool, which carries
    `pv37_gics_industry_group_number_di`.
    """
    from generator.template_fill import GROUP_NAMES, type_violation

    for fn, _ops in ALL_TEMPLATES:
        for seed in range(8):
            expr = _call(fn, rng=random.Random(seed))
            if not expr:
                continue
            problem = type_violation(expr, POOL, (), GROUP_NAMES)
            assert problem is None, f"{fn.__name__}: {problem} in {expr}"


def test_two_field_templates_use_their_arguments():
    """Each two-field template uses at least one of its field arguments."""
    for fn, _ops in ALL_TEMPLATES:
        if template_uses_pool(fn):
            continue
        expr = fn("UNIQUE_FIELD_A", "UNIQUE_FIELD_B")
        assert "UNIQUE_FIELD_A" in expr or "UNIQUE_FIELD_B" in expr, f"{fn.__name__} doesn't use any field: {expr}"


def test_pool_templates_degrade_when_keywords_are_missing():
    """Regression: pool templates were handed two field names, so `rng` was a
    string and every call raised `'str' object has no attribute 'choice'`
    mid-batch. A pool matching none of a template's keywords must now yield
    None — the generator reads that as 'fall back to a built-in' — not raise."""
    bare = ["pv37_omega_1", "pv37_delta_2"]
    for fn, _ops in ALL_TEMPLATES:
        if not template_uses_pool(fn):
            continue
        expr = fn(bare, random.Random(3))
        if fn in ANY_FIELD:
            assert isinstance(expr, str), f"{fn.__name__} should still fill: {expr!r}"
        else:
            assert expr is None, f"{fn.__name__} kept a missing-keyword pick: {expr}"
