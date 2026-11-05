"""Build helpers for multi-field expression generation."""

import random

import generator.weighted_selection as ws
from generator.combo_templates import (
    BLOCKED_3F_COMBOS,
    COMBO_3F,
    COMBO_3F_NAMES,
    COMBO_4F,
    COMBO_4F_NAMES,
    COMBO_5F,
    COMBO_5F_NAMES,
)
from generator.field_picker_matrix import pick_matrix
from generator.random_generator_dispatch import (  # noqa: F401
    HALF_REDRAWS,
    _call_template,
    _field_pool,
    _release,
)
from generator.registry import ALL_TEMPLATES


def _make_2field_expression(cell_context=None):
    """Generate a 2-field expression using weighted template selection."""
    fields = pick_matrix(count=2)
    if len(fields) < 2:
        return None
    fn, name = ws.weighted_choice(ALL_TEMPLATES, cell_context=cell_context)
    expr = _call_template(fn, fields)
    if expr:
        ws.record_expr_template(expr, name)
    return expr


def _make_3field(cell_context=None):
    """Generate a 3-field expression with combo wrapper."""
    fields = pick_matrix(count=3)
    if len(fields) < 3:
        return None
    fn, base_name = ws.weighted_choice(ALL_TEMPLATES, cell_context=cell_context)
    base = _call_template(fn, fields)
    if not base:
        return None
    w = random.choice([5, 10, 21, 63])
    allowed = [i for i, name in enumerate(COMBO_3F_NAMES) if (base_name, name) not in BLOCKED_3F_COMBOS]
    if not allowed:
        return None
    idx = random.choice(allowed)
    expr = COMBO_3F[idx](base, fields[2], w)
    ws.record_expr_template(expr, f"{base_name}+{COMBO_3F_NAMES[idx]}")
    return expr


def _make_4field(cell_context=None):
    """Generate a 4-field expression from two 2-field sub-expressions.

    Identical halves are redrawn: `rank(a - b)` (one of COMBO_4F) collapses to
    a constant zero when a == b, and the other combos degenerate too.
    """
    for _ in range(HALF_REDRAWS):
        a = _make_2field_expression(cell_context=cell_context)
        b = _make_2field_expression(cell_context=cell_context)
        if a and b and a != b:
            # Consume intermediate tracking — combo replaces it
            _release(a, b)
            idx = random.randrange(len(COMBO_4F))
            expr = COMBO_4F[idx](a, b)
            ws.record_expr_template(expr, f"combo_{COMBO_4F_NAMES[idx]}")
            return expr
        _release(a, b)
    return None


def _make_5field(cell_context=None):
    """Generate a 5-field expression from two 2-field sub-expressions plus extra.

    Identical halves are redrawn for the same reason as `_make_4field`.
    """
    for _ in range(HALF_REDRAWS):
        a = _make_2field_expression(cell_context=cell_context)
        b = _make_2field_expression(cell_context=cell_context)
        f5 = pick_matrix(count=1)
        if a and b and a != b and f5:
            # Consume intermediate tracking — combo replaces it
            _release(a, b)
            w = random.choice([5, 10, 21, 63])
            idx = random.randrange(len(COMBO_5F))
            expr = COMBO_5F[idx](a, b, f5[0], w)
            ws.record_expr_template(expr, f"combo_{COMBO_5F_NAMES[idx]}")
            return expr
        _release(a, b)
    return None
