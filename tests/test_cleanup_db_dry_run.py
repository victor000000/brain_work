"""cleanup_db's --dry-run must win over --execute."""

import sys

from core.db import connect
from tools import cleanup_db


def test_dry_run_wins_over_execute(tmp_path, monkeypatch):
    """`--dry-run --execute` is contradictory; the safe flag must win."""
    path = tmp_path / "brain.db"
    conn = connect(path)
    for table, column in (
        ("data_fields", "category_id"),
        ("datasets", "category_id"),
        ("dataset_categories", "id"),
        ("download_log", "subcategory_id"),
    ):
        conn.execute(f"CREATE TABLE {table} ({column} TEXT)")
    conn.execute("CREATE TABLE metadata (key TEXT, value TEXT)")
    conn.execute("INSERT INTO data_fields VALUES ('fundamental-data')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(cleanup_db, "DB_PATH", str(path))
    monkeypatch.setattr(sys, "argv", ["cleanup_db.py", "--dry-run", "--execute"])
    cleanup_db.main()

    conn = connect(path)
    assert conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0] == 1
    conn.close()
