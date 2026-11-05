"""Availability validation must not mistake a generation cap for a missing field."""

import random

import pytest

from core.db import connect
from core.db.schema_sql import SCHEMA_SQL
from generator import field_queries_matrix, field_validation_pools
from generator.field_validation_pools import validation_pools
from runner.explore_helpers.polish_crosscell import cross_cell_target
from runner.probe_validation import validate_probe
from runner.settings_factory import make_settings

DDL = """
CREATE TABLE data_fields (
    id TEXT, dataset_id TEXT, category_id TEXT, region TEXT, universe TEXT,
    delay INTEGER, type TEXT, coverage REAL, date_coverage REAL,
    alpha_count INTEGER, description TEXT
);
CREATE TABLE operators (name TEXT)
"""


@pytest.fixture
def conn(monkeypatch):
    c = connect(":memory:")
    c.executescript(SCHEMA_SQL)
    c.executescript(DDL)
    c.execute("INSERT INTO operators VALUES ('rank')")
    monkeypatch.setattr(field_validation_pools, "cached_dead_fields", lambda _conn: set())
    monkeypatch.setattr(field_queries_matrix, "cached_dead_fields", lambda _conn: set())
    yield c
    c.close()


def _field(
    conn, name, *, kind="MATRIX", category="pv", coverage=1, date_coverage=1, alpha_count=0, description="measurement"
):
    conn.execute(
        "INSERT INTO data_fields VALUES (?, 'pv1', ?, 'USA', 'TOP1000', 1, ?, ?, ?, ?, ?)",
        (name, category, kind, coverage, date_coverage, alpha_count, description),
    )


def test_probe_and_cross_cell_accept_eligible_field_outside_generation_sample(conn):
    for index in range(65):
        _field(conn, f"series_{index}")
    _field(conn, "wanted", coverage=0.75)

    sampled, _ = field_queries_matrix.query_matrix_fields(conn, "USA", 1, "TOP1000")
    assert len(sampled["pv1"]) == 60
    assert "wanted" not in sampled["pv1"]

    expression = "rank(wanted)"
    settings = make_settings("USA", "TOP1000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    validate_probe(conn, [expression], settings, ["idea:availability"])
    assert cross_cell_target(conn, [expression], ("HKG", "TOP800", 1), random.Random(1)) == ("USA", "TOP1000", 1)


@pytest.mark.parametrize("kind", ["MATRIX", "VECTOR", "GROUP"])
def test_validation_has_no_generation_limit_for_any_field_type(conn, kind):
    expected = {f"series_{index}" for index in range(125)}
    for name in expected:
        _field(conn, name, kind=kind)
    matrix, vectors, groups = validation_pools(conn, "USA", "TOP1000", 1)
    assert matrix | vectors | groups == expected
    assert matrix == (expected if kind == "MATRIX" else set())
    assert vectors == (expected if kind == "VECTOR" else set())
    assert groups == (expected if kind == "GROUP" else set())


def test_complete_validation_keeps_existing_scope_coverage_and_type_rules(conn, monkeypatch):
    _field(conn, "price")
    _field(conn, "child_price", category="pv-price-volume")
    _field(conn, "missing_coverage", coverage=0, alpha_count=3)
    _field(conn, "assets", category="fundamental")
    _field(conn, "ticker")
    _field(conn, "cluster_number", description="categorical cluster label")
    _field(conn, "thin_coverage", coverage=0.4)
    _field(conn, "short_history", date_coverage=0.4)
    _field(conn, "thin_vector", kind="VECTOR", coverage=0.2)
    _field(conn, "vector", kind="VECTOR", coverage=0.4)
    _field(conn, "partition", kind="GROUP", description="categorical cluster label")
    _field(conn, "dead_series")
    monkeypatch.setattr(field_validation_pools, "cached_dead_fields", lambda _conn: {"dead_series", "partition"})

    matrix, vectors, groups = validation_pools(conn, "USA", "TOP1000", 1)
    assert matrix == {"price", "child_price", "missing_coverage"}
    assert vectors == {"vector"}
    assert groups == {"partition"}


def test_probe_and_cross_cell_accept_a_genuine_group_argument(conn):
    _field(conn, "close")
    _field(conn, "partition", kind="GROUP", description="categorical cluster label")
    conn.execute("INSERT INTO operators VALUES ('group_neutralize')")
    expression = "group_neutralize(rank(close), partition)"
    settings = make_settings("USA", "TOP1000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    validate_probe(conn, [expression], settings, ["idea:group-contract"])
    assert cross_cell_target(conn, [expression], ("HKG", "TOP800", 1), random.Random(1)) == ("USA", "TOP1000", 1)


def test_vector_only_probe_references_scoped_data(conn):
    _field(conn, "event", kind="VECTOR")
    conn.execute("INSERT INTO operators VALUES ('vec_avg')")
    settings = make_settings("USA", "TOP1000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    validate_probe(conn, ["rank(vec_avg(event))"], settings, ["idea:vector-contract"])


@pytest.mark.parametrize("kind", ["MATRIX", "VECTOR"])
def test_taxonomy_depth_cannot_enter_numeric_validation_pool(conn, kind):
    _field(conn, "taxonomy_depth", kind=kind, description="Level of the sector within the hierarchy")
    _field(conn, "price_level", kind=kind, description="Closing price level")
    _field(conn, "sector_partition", kind="GROUP", description="Level of the sector within the hierarchy")
    matrix, vectors, groups = validation_pools(conn, "USA", "TOP1000", 1)
    assert "taxonomy_depth" not in matrix | vectors
    assert "price_level" in matrix | vectors
    assert "sector_partition" in groups
