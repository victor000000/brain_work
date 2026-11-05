"""A proven raw-price ratio must not become a price divided by beta."""

import json
import random
import re
from types import SimpleNamespace

import pytest

from generator.template_fill import fill_skeleton, generate_from_templates
from generator.template_fill_prices import price_contract
from generator.template_source_pick import next_expression
from generator.template_source_pool import load_pool, reset_cache

SHAPE = "rank((rank(-(1 - {f} / {f}))) + rank(ts_mean({f},21)))"
SOURCE = "rank((rank(-(1 - open / close))) + rank(ts_mean(score,21)))"
FIELDS = ["pv37_open_10", "pv37_close_11", "pv37_vwap_11", "beta"]
OPS = {"rank", "ts_mean"}


@pytest.fixture(autouse=True)
def price_cache(monkeypatch):
    from generator import field_picker

    cache = SimpleNamespace(matrix_by_dataset={"pv37": FIELDS[:-1]}, last_loaded=None)
    monkeypatch.setattr(field_picker, "get_cache", lambda: cache)
    reset_cache()
    yield
    reset_cache()


def test_price_pair_keeps_roles_and_target_reaches_the_unconstrained_leg():
    for seed in range(50):
        expr = fill_skeleton(SHAPE, FIELDS, random.Random(seed), first_pool=["beta"], example=SOURCE)
        assert "1 - pv37_open_10 / pv37_close_11" in expr
        assert "ts_mean(beta,21)" in expr


def test_repeated_prices_across_arithmetic_share_the_same_assignment():
    shape = "({f}/{f})+({f}-{f})/{f}"
    source = "(open/close)+(close-vwap)/vwap"
    expr = fill_skeleton(shape, FIELDS, random.Random(2), example=source)
    assert expr == "(pv37_open_10/pv37_close_11)+(pv37_close_11-pv37_vwap_11)/pv37_vwap_11"


def test_self_cancelling_units_and_nonmatching_examples_stay_generic():
    shape = "({f}-ts_mean({f},20))/ts_std_dev({f},20)"
    assert price_contract(shape, "(close-ts_mean(close,20))/ts_std_dev(close,20)") == ()
    assert price_contract(SHAPE, None) == ()
    assert price_contract(SHAPE, SOURCE.replace("21", "63")) == ()
    expr = fill_skeleton(shape, ["beta"], random.Random(3), example="(close-ts_mean(close,20))/ts_std_dev(close,20)")
    assert "beta" in expr


def test_production_and_batch_paths_pass_source_roles(tmp_path):
    rows = [{"skeleton": SHAPE, "example": SOURCE, "fillable_from_pv_option": True}]
    path = tmp_path / "templates.json"
    path.write_text(json.dumps(rows))
    expr = next_expression(FIELDS, random.Random(4), OPS, path, target_fields=["beta"])
    assert "1 - pv37_open_10 / pv37_close_11" in expr
    outputs = generate_from_templates(rows, FIELDS, 1, random.Random(4), OPS)
    assert len(outputs) == 1
    assert re.search(r"1 - pv37_open_10 / pv37_close_11", outputs[0])


def test_source_role_contracts_do_not_merge_with_anonymous_unit_shapes(tmp_path):
    path = tmp_path / "templates.json"
    path.write_text(
        json.dumps(
            [
                {"skeleton": SHAPE, "example": SOURCE, "fillable_from_pv_option": True},
                {
                    "skeleton": SHAPE,
                    "example": SOURCE.replace("open", "foo").replace("close", "bar"),
                    "fillable_from_pv_option": True,
                },
            ]
        )
    )
    assert len(load_pool(FIELDS, OPS, path)) == 2


def test_incompatible_pool_does_not_emit_a_mixed_unit_ratio():
    rows = [{"skeleton": SHAPE, "example": SOURCE}]
    assert generate_from_templates(rows, ["beta"], 1, random.Random(2), OPS) == []
