"""Preserve source-reference identity without equating anonymous variables."""

import json
import random

import pytest

from generator.template_fill import fill_skeleton, generate_from_templates
from generator.template_fill_bindings import infer_slot_bindings
from generator.template_source_pick import next_expression
from generator.template_source_pool import load_pool, reset_cache

SHAPE = "({f}-ts_mean({f},20))/ts_std_dev({f},20)"
EXAMPLE = "(close - ts_mean(close,20))/ts_std_dev(close,20)"
FIELDS = ["close", "volume", "returns"]
OPS = {"rank", "ts_mean", "ts_std_dev", "ts_corr", "group_neutralize", "group_rank", "vec_sum", "vec_avg", "add"}


def test_repeated_source_field_stays_one_field_with_a_mixed_unit_pool():
    bindings = infer_slot_bindings(SHAPE, EXAMPLE)
    assert bindings == (0, 0, 0)
    expected = "(close-ts_mean(close,20))/ts_std_dev(close,20)"
    assert fill_skeleton(SHAPE, FIELDS, random.Random(3), first_pool=["close"], slot_bindings=bindings) == expected
    # Before the correction this made a different, cross-unit expression.
    assert fill_skeleton(SHAPE, FIELDS, random.Random(3), first_pool=["close"]) != expected


def test_distinct_source_identifiers_remain_independent():
    bindings = infer_slot_bindings("ts_corr({f},{f},60)", "ts_corr(close,volume,60)")
    assert bindings == (0, 1)
    assert fill_skeleton("ts_corr({f},{f},60)", FIELDS, random.Random(8), slot_bindings=bindings) == fill_skeleton(
        "ts_corr({f},{f},60)", FIELDS, random.Random(8)
    )


@pytest.mark.parametrize(
    "example",
    [
        None,
        {},
        "rank(close)",
        "rank({f})",
        EXAMPLE + " trailing prose",
        EXAMPLE.replace("20", "63"),
        "(close-ts_mean(close,20))/ts_std_dev(close, 20) + 1",
    ],
)
def test_missing_or_nonmatching_examples_do_not_guess_a_binding(example):
    assert infer_slot_bindings(SHAPE, example) is None


def test_literal_tokens_and_whitespace_are_matched_safely():
    shape = 'group_rank({f},bucket(rank({f}),range="0, 1, 0.1"))'
    source = 'group_rank(close, bucket(rank(close), range="0, 1, 0.1"))'
    assert infer_slot_bindings(shape, source) == (0, 0)
    assert infer_slot_bindings(shape, source.replace("0, 1", "0,1")) is None
    assert infer_slot_bindings("rank({f})", "rank(nan)") is None


def test_runtime_pool_preserves_identity_and_keeps_different_identity_graphs(tmp_path):
    path = tmp_path / "templates.json"
    path.write_text(
        json.dumps(
            [
                {"skeleton": SHAPE, "example": EXAMPLE, "fillable_from_pv_option": True},
                {
                    "skeleton": SHAPE,
                    "example": "(close-ts_mean(open,20))/ts_std_dev(vwap,20)",
                    "fillable_from_pv_option": True,
                },
            ]
        )
    )
    reset_cache()
    try:
        rows = load_pool(FIELDS, OPS, path)
        assert len(rows) == 2
        assert {r["slot_bindings"] for r in rows} == {(0, 0, 0), (0, 1, 2)}
        # A one-row runtime path must actually pass the binding into filling.
        path.write_text(json.dumps([{"skeleton": SHAPE, "example": EXAMPLE, "fillable_from_pv_option": True}]))
        reset_cache()
        expr = next_expression(FIELDS, random.Random(7), OPS, path, target_fields=["close"])
        assert expr == "(close-ts_mean(close,20))/ts_std_dev(close,20)"
    finally:
        reset_cache()


def test_batch_generation_preserves_references_in_vector_positions():
    skeleton = "add(vec_avg({f}),vec_sum({f}))"
    rows = [{"skeleton": skeleton, "example": "add(vec_avg(option_vector),vec_sum(option_vector))"}]
    output = generate_from_templates(rows, FIELDS, 1, random.Random(9), OPS, vector_fields={"v1", "v2"})
    assert len(output) == 1
    assert output[0] in {"add(vec_avg(v1),vec_sum(v1))", "add(vec_avg(v2),vec_sum(v2))"}


def test_shared_group_and_series_references_use_typed_pools_with_spaces():
    shape = "group_neutralize({f}, {f})+group_rank({f}, {f})"
    source = "group_neutralize(close, industry)+group_rank(close, industry)"
    bindings = infer_slot_bindings(shape, source)
    assert bindings == (0, 1, 0, 1)
    expression = fill_skeleton(
        shape, FIELDS, random.Random(5), first_pool=["close"], group_fields=["sector"], slot_bindings=bindings
    )
    assert expression == "group_neutralize(close, sector)+group_rank(close, sector)"


def test_bad_binding_length_cannot_partially_apply():
    with pytest.raises(ValueError, match="every slot"):
        fill_skeleton(SHAPE, FIELDS, random.Random(1), slot_bindings=(0, 0))
