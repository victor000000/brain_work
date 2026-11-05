"""Prevent zero-signal price templates when one field fills both operands."""

import random

import pytest

from generator.field_picker.cache import FieldCache, set_cache
from generator.templates_brain_website_price_action import (
    high_low_spread,
    open_close_ratio,
    vwap_close_spread,
)


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize(
    ("template", "field"),
    [
        (vwap_close_spread, "vwap_30m_pre_close_2"),
        (high_low_spread, "high_low_price"),
        (open_close_ratio, "open_close_price"),
    ],
)
def test_colliding_price_roles_do_not_emit_constant_signals(template, field, cached):
    # Reproduce both the same-dataset picker and independent fallback path.
    cache = FieldCache()
    cache.matrix_by_dataset = {"pv": [field]} if cached else {}
    set_cache(cache)
    try:
        assert template([field], random.Random(17)) is None
    finally:
        set_cache(FieldCache())
