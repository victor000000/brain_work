"""Connection + idempotent init_tables coverage.

`get_conn()` points at the live DB, so its DB_PATH is monkeypatched to a
throwaway file — these tests write DDL and must never touch production.
"""

from core.db import connect, init_tables


def _tmp_conn(tmp_path):
    return connect(tmp_path / "test.duckdb")


def test_get_conn_opens_the_database(tmp_path, monkeypatch):
    """get_conn() creates the file on first use and reads its own writes.

    (Under SQLite this also asserted journal_mode=wal; DuckDB has no
    equivalent knob — durability is the write-ahead log's, always on.)
    """
    from core.db import connection as db_connection

    db_path = tmp_path / "test.duckdb"
    monkeypatch.setattr(db_connection, "DB_PATH", str(db_path))
    conn = db_connection.get_conn()
    try:
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        assert conn.execute("SELECT x FROM t").fetchone()[0] == 1
    finally:
        conn.close()
    assert db_path.exists()


def test_init_tables(tmp_path):
    """Table initialization should be idempotent."""
    conn = _tmp_conn(tmp_path)
    init_tables(conn)
    init_tables(conn)  # Second call should not fail.

    tables = conn.execute(
        "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='main' AND table_type='BASE TABLE'"
    ).fetchall()
    table_names = {t[0] for t in tables}
    assert "simulations" in table_names
    assert "alpha_results" in table_names
    assert "submission_checks" in table_names
    assert "alpha_check_summary" in table_names
    conn.close()
