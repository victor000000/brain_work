"""Which mined skeletons are usable: shape, adjacent slots, field tokens."""

from generator.template_fill import is_usable
from tests.test_template_fill_helpers import FIELDS


def test_is_usable_accepts_slotted_skeletons():
    assert is_usable("ts_rank({f},20)", FIELDS)


def test_is_usable_rejects_placeholder_identifiers():
    """`ts_delta(x,d)` parses but x and d are not fields — it cannot produce a real alpha."""
    assert not is_usable("ts_delta(x,d)", FIELDS)
    assert not is_usable("vector_neut(x,y)", FIELDS)


def test_is_usable_rejects_adjacent_slots():
    """Prose that mentions an operator normalises into glued slots.

    `looks_like_alpha` in the miner accepts any line containing an operator
    call, so an English sentence mentioning `ts_backfill(x, days)` passes. Once
    whitespace is stripped its words become adjacent `{f}` runs, and filling
    them produces identifiers like `sectorpv98_vwap_1430_backfill` — which
    fastplus accepts, because it treats any identifier as a call or a variable.
    """
    assert not is_usable("min({f}{f},20)", FIELDS)
    assert not is_usable("min({f} {f},20)", FIELDS)
    assert not is_usable("Related{f}{f}{f}a{f}", FIELDS)


def test_is_usable_keeps_templates_with_separated_slots():
    """Two slots is fine when something separates them."""
    assert is_usable("ts_corr({f},{f},60)", FIELDS)
    assert is_usable("ts_corr({f} - {f},{f},60)", FIELDS)


def test_is_usable_rejects_skeletons_that_cannot_parse():
    """Shape is judged at load, with slots stood in by a placeholder.

    Prose fragments that merely contain an operator call pass every token
    check (slots present, operators real, fields real) and used to be kept in
    the pool until filling failed — a wasted fill and fastplus parse on every
    draw. ts_corr's three arguments and the prose tail are both shape errors.
    """
    assert not is_usable("排序成交量：rank({f})对当日的成交量进行排序。", FIELDS)  # noqa: RUF001
    assert not is_usable("{f}=bucket(rank({f}),range='0,1,0.1')", FIELDS)
    assert not is_usable("ts_corr({f} - {f},60)", FIELDS)  # ts_corr needs 3 args


def test_is_usable_accepts_concrete_known_fields():
    assert is_usable("rank(close)", FIELDS)
    assert is_usable("ts_corr(close,volume,60)", FIELDS)


def test_is_usable_rejects_slotless_skeletons_that_read_no_field():
    """A slotless skeleton with no field token is a constant, not an alpha.

    The corpus holds `ts_av_diff(185,5)` and friends: valid syntax, no data.
    They cost a simulation and contribute nothing, so the pool must not offer
    them just because they happen to contain no *unknown* token.
    """
    assert not is_usable("ts_av_diff(185,5)", FIELDS)
    assert not is_usable("ts_av_diff(0.9,4)", FIELDS)
    assert not is_usable("nan", FIELDS)
    # Group names alone are not data either.
    assert not is_usable("group_cartesian_product(sector,industry)", FIELDS)


def test_is_usable_rejects_a_slot_as_densify_argument():
    """`densify` needs a group of the target cell, and a slot cannot supply one.

    Slots are filled from the union of every cell's fields, so `densify({f})`
    renders whatever field the draw lands on — a GROUP in one cell is a plain
    series, or nothing, where the batch actually goes. The platform answers
    `Incompatible unit for input of "densify" at index 0, expected
    "Unit[Group:1]"` and charges the simulation. Measured 2026-10-11: 0 of
    214,359 stored alphas contain `densify(`, against 5-15 emissions a day — a
    100% failure rate. Three of the four shapes that emit it are these.
    """
    assert not is_usable("group_zscore(ts_av_diff({f},66),densify({f}))", FIELDS)
    assert not is_usable("-group_neutralize(ts_av_diff({f},252),densify({f}))", FIELDS)
    # Whitespace does not launder it.
    assert not is_usable("group_neutralize(ts_rank({f},252), densify( {f} ))", FIELDS)


def test_is_usable_keeps_literal_and_nested_densify_arguments():
    """Only the slot form is rejected; the forms that can work stay in the pool.

    A built-in group name is valid in every cell — the fourth proven-corpus
    skeleton uses `densify(sector)` — and a nested `bucket` builds the group
    itself, which is the construct `cap_decile_neutralized` relies on for its
    group argument.
    """
    assert is_usable("rank(group_rank(ts_zscore({f},63),densify(sector)))", FIELDS)
    assert is_usable("group_zscore({f},densify(bucket(rank(cap),range='0,1,0.1')))", FIELDS)
