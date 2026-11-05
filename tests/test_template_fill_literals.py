"""Out-of-scope literals in mined skeletons (the `sales` leak)."""

import random

from generator.template_fill import (
    field_violation,
    filled_expression_problem,
    generate_from_templates,
    is_usable,
    unknown_field_tokens,
)
from tests.test_template_fill_helpers import FIELDS, OPS

# The miner normalises datafields to {f}, but it left fundamental fields
# literal in ~91 skeletons: the filler used to accept any skeleton with a
# slot, so `-ts_backfill(zscore({f}/sales),65)` filled and validated and
# spent simulations on `sales`, which the pv/option restriction put out of
# reach. Literals must be checked on *every* skeleton, slotted or not.
REAL_LEAKY_SKELETONS = [
    "-ts_backfill(zscore({f}/sales),65)*(ts_rank({f},20))",
    "rank({f}/assets)",
    "ts_delta(dividend,{f})",
    "group_neutralize({f},sector)*sharesout",
    "sales/ts_mean({f},20)",
]


def test_is_usable_rejects_out_of_scope_literals_in_slotted_skeletons():
    for skeleton in REAL_LEAKY_SKELETONS:
        assert not is_usable(skeleton, FIELDS, OPS), skeleton


def test_is_usable_accepts_pool_fields_in_the_same_positions():
    for skeleton in [
        "-ts_backfill(zscore({f}/volume),65)*(ts_rank({f},20))",
        "group_neutralize({f},industry)",
        "ts_delta(close,{f})",
    ]:
        assert is_usable(skeleton, FIELDS, OPS), skeleton


def test_unknown_field_tokens_reports_literal_and_slot_values():
    assert unknown_field_tokens("rank({f}/sales)", FIELDS) == {"sales"}
    assert unknown_field_tokens("rank({f}/volume)", FIELDS) == set()


def test_filled_expression_problem_rejects_a_leaked_literal():
    problem = filled_expression_problem("rank(close/sales)", FIELDS, OPS)
    assert problem is not None and "sales" in problem


def test_generate_from_templates_never_emits_out_of_scope_fields():
    templates = [{"skeleton": s} for s in REAL_LEAKY_SKELETONS]
    templates.append({"skeleton": "ts_rank({f},20)"})
    out = generate_from_templates(templates, FIELDS, count=10, rng=random.Random(4), known_operators=OPS)
    assert out
    for expr in out:
        assert unknown_field_tokens(expr, FIELDS) == set(), expr


def test_field_violation_is_none_for_builtin_group_names():
    assert field_violation("group_rank(close,industry)", FIELDS) is None


def test_uppercase_calls_are_seen_and_rejected():
    """`Max(` is either an invented operator or a mis-cased field used as one."""
    assert not is_usable("Max({f},5)", FIELDS, OPS)
    assert unknown_field_tokens("Max(Vvolume,5)", FIELDS) == {"Vvolume"}
    assert not is_usable("STR({f})", FIELDS, OPS)
