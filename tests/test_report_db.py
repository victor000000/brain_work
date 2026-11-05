"""Reports share snapshots and never silently substitute an explicit source."""

import pytest

from core.db import OperationalError, connect, connect_for_reading
from tools import report_db


def _database(path):
    conn = connect(str(path))
    conn.execute("CREATE TABLE marker (value INTEGER)")
    conn.execute("INSERT INTO marker VALUES (42)")
    conn.close()
    return path


def test_report_connection_shares_a_read_only_snapshot(tmp_path):
    path = _database(tmp_path / "snapshot.duckdb")
    reader = connect_for_reading(str(path))
    try:
        conn, source = report_db.open_report_db(path)
        try:
            assert source == str(path)
            assert conn.execute("SELECT * FROM marker").fetchone() == (42,)
            with pytest.raises(OperationalError):
                conn.execute("INSERT INTO marker VALUES (99)")
        finally:
            conn.close()
        assert reader.execute("SELECT count(*) FROM marker").fetchone()[0] == 1
    finally:
        reader.close()


def test_live_fallback_orders_real_instants_and_skips_unreadable_backups(tmp_path, monkeypatch, capsys):
    live = tmp_path / "live.duckdb"
    monkeypatch.setattr(report_db, "DB_PATH", str(live))
    _database(tmp_path / "live.duckdb.bak-20261016T1527Z-older")
    newest = _database(tmp_path / "live.duckdb.bak-20261016T152723Z-newer")
    (tmp_path / "live.duckdb.bak-20261016T152724Z-incomplete").write_text("partial copy")
    _database(tmp_path / "live.duckdb.bak-20261016T160000Z.wal")
    _database(tmp_path / "live.duckdb.bak-before-anything")
    conn, source = report_db.open_report_db()
    try:
        assert source == str(newest)
        assert conn.execute("SELECT * FROM marker").fetchone() == (42,)
        assert newest.name in capsys.readouterr().out
    finally:
        conn.close()


def test_explicit_unavailable_snapshot_does_not_fall_back(tmp_path, monkeypatch):
    live = tmp_path / "live.duckdb"
    monkeypatch.setattr(report_db, "DB_PATH", str(live))
    _database(tmp_path / "live.duckdb.bak-20261016T1527Z")
    with pytest.raises(OperationalError):
        report_db.open_report_db(tmp_path / "requested.duckdb")


def test_live_fallback_explains_when_no_checkpoint_is_readable(tmp_path, monkeypatch):
    monkeypatch.setattr(report_db, "DB_PATH", str(tmp_path / "live.duckdb"))
    with pytest.raises(OperationalError, match="no readable timestamped backup"):
        report_db.open_report_db()
