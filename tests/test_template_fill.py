"""Filling mined skeletons: slot substitution and pyramid targeting."""

import random

import pytest

from generator.template_fill import fill_skeleton, slot_count
from tests.test_template_fill_helpers import FIELDS


def test_slot_count_counts_placeholders():
    assert slot_count("rank(close)") == 0
    assert slot_count("ts_rank({f},20)") == 1
    assert slot_count("trade_when({f},{f},-1)") == 2


def test_fill_replaces_every_slot():
    out = fill_skeleton("ts_rank({f},20)", FIELDS, random.Random(1))
    assert "{f}" not in out
    assert out.startswith("ts_rank(") and out.endswith(",20)")


def test_fill_leaves_slotless_skeletons_untouched():
    assert fill_skeleton("rank(close)", FIELDS, random.Random(1)) == "rank(close)"


def test_fill_only_uses_fields_from_the_pool():
    rng = random.Random(7)
    for _ in range(50):
        out = fill_skeleton("ts_corr({f},{f},60)", FIELDS, rng)
        for f in FIELDS:
            out = out.replace(f, "", 1) if f in out else out
        assert out.count("(") == out.count(")")


def test_fill_is_deterministic_for_a_seeded_rng():
    a = fill_skeleton("ts_rank({f},20)", FIELDS, random.Random(42))
    b = fill_skeleton("ts_rank({f},20)", FIELDS, random.Random(42))
    assert a == b


def test_fill_raises_on_empty_field_pool():
    with pytest.raises(ValueError):
        fill_skeleton("ts_rank({f},20)", [], random.Random(1))


# --- pyramid targeting --------------------------------------------------
#
# pick_matrix guarantees at least one field from the target pyramid for
# built-in templates. Mined templates bypassed that entirely, so a quarter of
# generated output ignored the target the explorer had just picked.


def test_fill_uses_the_preferred_pool_for_the_first_slot():
    out = fill_skeleton("ts_corr({f},{f},60)", FIELDS, random.Random(2), first_pool=["cap"])
    assert "cap" in out


def test_fill_with_preferred_pool_leaves_other_slots_to_the_main_pool():
    rng = random.Random(5)
    for _ in range(20):
        out = fill_skeleton("ts_corr({f},{f},60)", FIELDS, rng, first_pool=["cap"])
        assert out.count("cap") >= 1
        assert out.count("(") == out.count(")")


def test_fill_without_preferred_pool_is_unchanged():
    a = fill_skeleton("ts_rank({f},20)", FIELDS, random.Random(9))
    b = fill_skeleton("ts_rank({f},20)", FIELDS, random.Random(9), first_pool=None)
    assert a == b


def test_fill_ignores_an_empty_preferred_pool():
    """An unsatisfiable target must not break generation."""
    out = fill_skeleton("ts_rank({f},20)", FIELDS, random.Random(1), first_pool=[])
    assert "{f}" not in out
