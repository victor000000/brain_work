"""cleanup_db --backup copies a consistent database.

DuckDB permits a single process per database file, so a backup can only be
taken by the process that holds it: CHECKPOINT folds the write-ahead log into
the main file and the copy is then complete. What must not happen is a backup
that silently misses recent commits, or one that runs while another process
is using the database.
"""

from core.db import connect
from tests import test_cleanup_db_backup_helpers as helpers
from tools import cleanup_db

# Bound here rather than imported by name: a direct import of `live_db` would
# be shadowed by the test parameters of the same name (ruff F811).
live_db = helpers.live_db


def test_backup_copies_committed_rows(live_db, tmp_path):
    dest = tmp_path / "backup.duckdb"
    assert cleanup_db.backup_database(str(dest)) is True

    conn = connect(dest, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 3
    conn.close()


def test_backup_includes_writes_not_yet_checkpointed(live_db, tmp_path):
    """The CHECKPOINT is what makes the copy complete."""
    _path, writer = live_db
    writer.execute("INSERT INTO t VALUES (4)")
    writer.commit()

    dest = tmp_path / "fresh.duckdb"
    assert cleanup_db.backup_database(str(dest)) is True
    conn = connect(dest, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 4
    conn.close()


def test_active_writer_is_false_when_idle(live_db):
    assert cleanup_db.active_writer() is False
