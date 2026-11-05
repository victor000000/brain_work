"""Cross-cell polish: the target must be able to run the expression, or nothing.

A cross-cell re-run spends a simulation, so both gates are tested here — the
field must exist in the target pool, and the expression must still satisfy the
target's operator-argument types.
"""

import random

import pytest

from core.db import connect
from core.db.schema_sql import SCHEMA_SQL
from runner.explore_helpers.polish_cell import CROSS_CELL_EVERY, pick_cell
from runner.explore_helpers.polish_crosscell import cells_holding, cross_cell_target

DDL = """
CREATE TABLE data_fields (
    id TEXT, dataset_id TEXT, category_id TEXT, region TEXT, delay INTEGER,
    universe TEXT, type TEXT, coverage REAL, date_coverage REAL,
    alpha_count INTEGER, description TEXT
);
CREATE TABLE operators (name TEXT)
"""


def _field(conn, name, region, universe, delay=1, kind="MATRIX", category="pv"):
    conn.execute(
        "INSERT INTO data_fields VALUES (?,?,?,?,?,?,?, 0.9, 0.9, 7, NULL)",
        (name, f"{category}1", category, region, delay, universe, kind),
    )


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript(SCHEMA_SQL)
    c.executescript(DDL)
    c.executemany("INSERT INTO operators VALUES (?)", [("rank",), ("ts_delta",)])
    # `close` lives in HKG and USA; `only_hkg` is HKG/TOP800-only.
    for region, universe in (("HKG", "TOP800"), ("USA", "TOP1000")):
        _field(c, "close", region, universe)
        _field(c, "volume", region, universe)
    _field(c, "only_hkg", "HKG", "TOP800")
    c.commit()
    yield c
    c.close()


def test_cells_holding_requires_every_field(conn):
    assert ("USA", "TOP1000", 1) in cells_holding(conn, {"close", "volume"})
    # The exclusive name kills the USA candidate.
    assert ("USA", "TOP1000", 1) not in cells_holding(conn, {"close", "only_hkg"})


def test_no_fields_is_not_a_candidate_set(conn):
    assert cells_holding(conn, set()) == []


def test_target_prefers_another_region(conn):
    target = cross_cell_target(conn, ["rank(close)"], ("HKG", "TOP800", 1), random.Random(1))
    assert target is not None and target[0] == "USA"


def test_a_field_the_other_region_lacks_yields_no_target(conn):
    expr = "rank(close) + rank(only_hkg)"
    assert cross_cell_target(conn, [expr], ("HKG", "TOP800", 1), random.Random(1)) is None


def test_a_group_field_in_a_series_position_is_not_retargeted(conn):
    """The gates must compose: a field that exists in the target but is typed
    GROUP there is still refused, because the expression would come back
    `Incompatible unit ... found "Unit[Group:1]"` and cost a simulation."""
    _field(conn, "grp", "USA", "TOP1000", kind="GROUP")
    _field(conn, "grp", "HKG", "TOP800", kind="GROUP")
    expr = "ts_delta(grp,3)"  # reads a group as a series
    assert cross_cell_target(conn, [expr], ("HKG", "TOP800", 1), random.Random(1)) is None


def _candidate(conn, aid, expr, region="HKG", universe="TOP800", attempts=0):
    conn.execute(
        "INSERT INTO polish_candidates (alpha_id, expression, region, universe, delay,"
        " neutralization, attempts, created_at) VALUES (?,?,?,?,1,'SLOW',?,'now')",
        (aid, expr, region, universe, attempts),
    )
    conn.commit()


def test_pick_cell_stays_home_on_ordinary_batches(conn):
    rows = _seed(conn)
    cell, cands = pick_cell(conn, rows, 3, random.Random(1), batch_idx=1)
    assert cell == ("HKG", "TOP800", 1)
    assert [c[0] for c in cands] == ["A1"]


def test_pick_cell_moves_every_cross_cell_batch(conn):
    rows = _seed(conn)
    cell, _cands = pick_cell(conn, rows, 3, random.Random(1), batch_idx=CROSS_CELL_EVERY)
    assert cell[0] == "USA"


def test_pick_cell_without_a_batch_index_never_moves(conn):
    """`batch_idx` is optional; an unattributable run must not move."""
    rows = _seed(conn)
    cell, _cands = pick_cell(conn, rows, 3, random.Random(1), batch_idx=None)
    assert cell == ("HKG", "TOP800", 1)


def _seed(conn):
    _candidate(conn, "A1", "rank(close)")
    return conn.execute(
        "SELECT alpha_id, expression, region, universe, delay, neutralization, attempts FROM polish_candidates"
    ).fetchall()


def test_an_unconfigured_cell_is_never_a_target(conn):
    """`data_fields` carries cells the platform refuses to simulate.

    Measured live 2026-10-11: a polish batch went to `ALL/LARGE/d1` and came
    back `HTTP 400 {"settings": {"region": ["Region ALL is not available for
    simulation type REGULAR."]}}` — a batch spent on a cell that cannot run
    anything. EVERY field the expression needs lives there, which is exactly why
    the field-existence gate alone cannot catch it.
    """
    _field(conn, "close", "ALL", "LARGE")
    _field(conn, "volume", "ALL", "LARGE")
    assert ("ALL", "LARGE", 1) not in cells_holding(conn, {"close", "volume"})

    # And with no configured alternative holding both, there is no target at
    # all rather than a bad one.
    assert cross_cell_target(conn, ["rank(volume) + rank(only_hkg)"], ("HKG", "TOP800", 1), random.Random(2)) is None
