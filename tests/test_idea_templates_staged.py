"""The staged menu uses scoped types, one dataset per residual and valid syntax."""

import random

import pytest

from core.db import connect
from generator import field_validation_pools
from generator.field_picker import get_cache
from generator.idea_templates_staged import (
    STAGED_IDEA_CONTROLS,
    STAGED_IDEA_TEMPLATES,
    IdeaPools,
    staged_pools,
    vector_dispersion_stddev,
    vector_residual,
)
from generator.registry import ALL_TEMPLATES
from generator.template_fill import filled_expression_problem

POOLS = IdeaPools(
    ("close", "volume", "returns", "pv1_close", "pv1_open"),
    ("event",),
    ("partition",),
    {"pv1": ("pv1_close", "pv1_open")},
)
OPS = {
    "rank",
    "vec_stddev",
    "vec_range",
    "trade_when",
    "less",
    "ts_count_nans",
    "ts_mean",
    "last_diff_value",
    "greater",
    "group_count",
    "vector_neut",
    "ts_backfill",
}


@pytest.mark.parametrize("template", (*STAGED_IDEA_TEMPLATES, *STAGED_IDEA_CONTROLS))
def test_staged_shapes_use_the_production_contracts(template):
    for seed in range(30):
        expression = template(POOLS, random.Random(seed))
        assert expression is not None
        assert filled_expression_problem(expression, POOLS.matrix, OPS, POOLS.vectors, POOLS.groups) is None
    assert template not in {fn for fn, _ in ALL_TEMPLATES}


@pytest.mark.parametrize("template", (*STAGED_IDEA_TEMPLATES, *STAGED_IDEA_CONTROLS))
def test_missing_roles_emit_nothing(template):
    assert template(IdeaPools((), (), (), {}), random.Random(1)) is None


def test_vector_reducer_never_draws_from_matrix_even_when_the_name_looks_like_a_vector():
    pools = IdeaPools(("pv1_vec_signal",), (), (), {})
    assert vector_dispersion_stddev(pools, random.Random(0)) is None


def test_residual_never_pairs_fields_from_different_datasets():
    pools = IdeaPools(("one", "two"), (), (), {"pv1": ("one",), "pv2": ("two",)})
    assert vector_residual(pools, random.Random(0)) is None


def test_scoped_metadata_defines_vector_types_and_pv_residual_membership(monkeypatch):
    from tests.test_field_validation_pools import DDL

    conn = connect(":memory:")
    conn.executescript(DDL)
    monkeypatch.setattr(field_validation_pools, "cached_dead_fields", lambda conn: set())
    rows = [
        ("plain_event", "pv1", "pv", "USA", "TOP1000", 1, "VECTOR", 1, 1, 0, "measurement"),
        ("vec_named_matrix", "pv1", "pv-price-volume", "USA", "TOP1000", 1, "MATRIX", 1, 1, 0, "measurement"),
        ("pv1_close", "pv1", "pv", "USA", "TOP1000", 1, "MATRIX", 1, 1, 0, "measurement"),
        ("pv1_foreign_option", "pv1", "option", "USA", "TOP1000", 1, "MATRIX", 1, 1, 0, "measurement"),
        ("assets", "fnd1", "fundamental", "USA", "TOP1000", 1, "MATRIX", 1, 1, 0, "measurement"),
    ]
    conn.executemany("INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    try:
        pools = staged_pools(conn, "USA", "TOP1000", 1)
        assert pools.vectors == ("plain_event",)
        assert pools.pv_by_dataset == {"pv1": ("pv1_close", "vec_named_matrix")}
        assert "pv1_foreign_option" in pools.matrix
        assert "assets" not in pools.matrix
    finally:
        conn.close()


def test_staged_sweep_restores_the_loaded_cell_on_failure(monkeypatch):
    from tools import staged_ideas

    cache = get_cache()
    old_cell = cache.last_loaded
    monkeypatch.setattr(staged_ideas, "REGION_CONFIGS", [("USA", "TOP1000", 1)])
    monkeypatch.setattr(staged_ideas, "load_operator_names", lambda conn: OPS)
    monkeypatch.setattr(staged_ideas, "staged_pools", lambda *args: POOLS)

    def fail(*args):
        raise RuntimeError("validation failed")

    monkeypatch.setattr(staged_ideas, "filled_expression_problem", fail)
    with pytest.raises(RuntimeError, match="validation failed"):
        staged_ideas.sweep(None, 1, 42)
    assert cache.last_loaded == old_cell
