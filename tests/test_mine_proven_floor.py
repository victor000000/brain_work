"""The floor-proven corpus is drawn from alphas, so its miners are pure SQL+text."""

import pytest

from core.db import connect
from tools import mine_proven_floor


def make_conn(rows, target=":memory:"):
    """alpha_results rows as (region, delay, universe, expression, is_sharpe)."""
    conn = connect(target)
    conn.execute(
        """
        CREATE TABLE alpha_results (
            alpha_id TEXT, region TEXT, delay INTEGER, universe TEXT,
            expression TEXT, is_sharpe REAL, created_at TEXT
        )
        """
    )
    conn.execute("CREATE TABLE data_fields (id TEXT)")
    conn.executemany("INSERT INTO data_fields VALUES (?)", [("close",), ("volume",), ("vwap",)])
    conn.execute("CREATE TABLE operators (name TEXT)")
    conn.executemany(
        "INSERT INTO operators VALUES (?)",
        [
            (name,)
            for name in ("rank", "ts_mean", "group_neutralize", "winsorize", "trade_when", "ts_regression", "bucket")
        ],
    )
    for i, (region, delay, universe, expr, sharpe) in enumerate(rows):
        conn.execute(
            "INSERT INTO alpha_results VALUES (?,?,?,?,?,?,?)",
            (f"a{i}", region, delay, universe, expr, sharpe, "2026-10-11T00:00:00-04:00"),
        )
    conn.commit()
    return conn


def test_keeps_shapes_that_reached_their_cells_floor():
    conn = make_conn(
        [
            ("USA", 1, "TOP3000", "rank(ts_mean(close,60))", 1.9),  # floor 1.58
            ("USA", 1, "TOP3000", "rank(ts_mean(volume,60))", 2.1),
            ("USA", 1, "TOP3000", "rank(ts_mean(vwap,60))", 0.4),  # below the floor
        ]
    )
    rows, _shapes, _alphas = mine_proven_floor.mine(conn, days=30, min_evidence=2)
    assert [r["skeleton"] for r in rows] == ["rank(ts_mean({f},60))"]
    assert rows[0]["alpha_count"] == 2
    assert rows[0]["best_sharpe"] == 2.1


def test_the_cells_own_floor_is_used_not_a_global_one():
    """CHN's floor is 2.07; a 1.9 alpha is above EUR's 1.58 and below CHN's."""
    conn = make_conn(
        [
            # Same shape twice per cell, so a skeleton's presence can only come
            # from the cell whose floor the alphas cleared.
            ("CHN", 1, "TOP2000U", "rank(ts_mean(close,60))", 1.9),
            ("CHN", 1, "TOP2000U", "rank(ts_mean(volume,60))", 1.7),
            ("EUR", 1, "TOP2500", "rank(ts_mean(vwap,252))", 1.9),
            ("EUR", 1, "TOP2500", "rank(ts_mean(close,252))", 1.7),
        ]
    )
    rows, _shapes, _alphas = mine_proven_floor.mine(conn, days=30, min_evidence=1)
    kept = {r["skeleton"] for r in rows}
    assert "rank(ts_mean({f},60))" not in kept, "CHN's two are under its own 2.07 floor"
    assert "rank(ts_mean({f},252))" in kept, "EUR's 1.7 clears EUR's 1.58"


def test_a_shape_with_a_field_we_no_longer_hold_is_dropped():
    """The database was narrowed to pv/option on 2026-10-02."""
    conn = make_conn(
        [
            ("USA", 1, "TOP3000", "rank(ts_mean(assets,60))", 2.0),
            ("USA", 1, "TOP3000", "rank(ts_mean(assets,61))", 2.0),
        ]
    )
    rows, _shapes, _alphas = mine_proven_floor.mine(conn, days=30, min_evidence=1)
    assert rows == []


def test_min_evidence_is_a_reproducibility_bar():
    conn = make_conn([("USA", 1, "TOP3000", "rank(ts_mean(close,60))", 1.9)])
    assert mine_proven_floor.mine(conn, days=30, min_evidence=2)[0] == []
    assert len(mine_proven_floor.mine(conn, days=30, min_evidence=1)[0]) == 1


@pytest.mark.parametrize("group", ["sector", "industry", "subindustry", "market", "country", "exchange", "currency"])
def test_builtin_groups_survive_without_dataset_metadata(group):
    """Built-in groups remain valid when a scoped field table excludes them."""
    conn = make_conn([("USA", 1, "TOP3000", f"group_neutralize(close, {group})", 1.9)])
    rows, shapes, _alphas = mine_proven_floor.mine(conn, days=30, min_evidence=1)
    assert shapes == 1
    assert rows[0]["skeleton"] == f"group_neutralize({{f}}, {group})"
    assert rows[0]["pv_option_fields"] == ["close"]


@pytest.mark.parametrize(
    ("expression", "skeleton"),
    [
        ("winsorize(close, std=4.0)", "winsorize({f}, std=4.0)"),
        ("trade_when(close > 0, volume, nan)", "trade_when({f} > 0, {f}, nan)"),
        ("ts_regression(close, volume, 60, rettype=0)", "ts_regression({f}, {f}, 60, rettype=0)"),
        ("bucket(rank(close), range='0,1,0.1')", "bucket(rank({f}), range='0,1,0.1')"),
    ],
)
def test_operator_keywords_and_literals_are_preserved(expression, skeleton):
    conn = make_conn([("USA", 1, "TOP3000", expression, 1.9)])
    rows, shapes, _alphas = mine_proven_floor.mine(conn, days=30, min_evidence=1)
    assert shapes == 1
    assert rows[0]["skeleton"] == skeleton


@pytest.mark.parametrize(
    "expression",
    [
        "group_neutralize(assets, industry)",
        "winsorize(assets, std=4.0)",
        "trade_when(close > 0, assets, nan)",
        "winsorize(std_assets, std=4.0)",
        "group_neutralize(close, Industry)",
        "winsorize(close, Std=4.0)",
    ],
)
def test_builtin_tokens_do_not_hide_unknown_fields(expression):
    conn = make_conn([("USA", 1, "TOP3000", expression, 1.9)])
    rows, shapes, _alphas = mine_proven_floor.mine(conn, days=30, min_evidence=1)
    assert rows == []
    assert shapes == 0


@pytest.mark.parametrize("expression", ["industry(close)", "std(close)", "close(volume)"])
def test_allowed_value_names_cannot_be_called_as_operators(expression):
    conn = make_conn([("USA", 1, "TOP3000", expression, 1.9)])
    assert mine_proven_floor.mine(conn, days=30, min_evidence=1)[0] == []


def test_main_can_mine_a_snapshot_while_another_reader_is_open(tmp_path, monkeypatch, capsys):
    path = str(tmp_path / "floor_snapshot.duckdb")
    writer = make_conn([("USA", 1, "TOP3000", "winsorize(close, std=4.0)", 1.9)], target=path)
    writer.close()
    reader = connect(path, read_only=True)
    monkeypatch.setattr("sys.argv", ["mine_proven_floor", "--db", path, "--min-evidence", "1", "--dry-run"])
    try:
        assert mine_proven_floor.main() == 0
        assert reader.execute("SELECT expression FROM alpha_results").fetchone() == ("winsorize(close, std=4.0)",)
        output = capsys.readouterr().out
        assert "scanned 1 alphas" in output
        assert "winsorize({f}, std=4.0)" in output
        assert "dry run: nothing written" in output
    finally:
        reader.close()
    # The miner must release the connection it opened before returning.
    reopened = connect(path)
    reopened.close()


def test_main_keeps_an_injected_connection_open(monkeypatch, tmp_path):
    conn = make_conn([("USA", 1, "TOP3000", "rank(close)", 1.9)])
    # A caller-owned connection takes precedence over the CLI database path.
    monkeypatch.setattr("sys.argv", ["mine_proven_floor", "--db", str(tmp_path / "missing.duckdb"), "--dry-run"])
    try:
        assert mine_proven_floor.main(conn=conn) == 0
        assert conn.execute("SELECT COUNT(*) FROM alpha_results").fetchone() == (1,)
    finally:
        conn.close()
