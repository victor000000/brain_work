"""refresh_pyramid_targets persistence: schema migration and storage edges.

The history table is seeded by archiving whatever the pre-fix `pyramid_targets`
table already held; these tests pin the migration and the row-level edge cases
(NULL periods, empty batches, the history primary key).
"""

from core.db import connect
from tests.test_refresh_pyramid_targets_helpers import _db, _row, _seed_old_snapshot
from tools.refresh_pyramid_targets.persist import HISTORY_TABLE, ensure_schema, upsert


def test_ensure_schema_archives_the_existing_snapshot(tmp_path):
    path = _db(tmp_path)
    _seed_old_snapshot(path)

    conn = connect(path)
    archived = ensure_schema(conn)
    conn.close()

    assert archived == 1
    conn = connect(path)
    rows = conn.execute(f"SELECT region, delay, category, alpha_count, period_start FROM {HISTORY_TABLE}").fetchall()
    assert rows == [("USA", 1, "pv", 1, "2026-04-01")]
    # the current table is untouched by the migration
    assert conn.execute("SELECT alpha_count FROM pyramid_targets").fetchone()[0] == 1
    conn.close()


def test_ensure_schema_is_idempotent(tmp_path):
    path = _db(tmp_path)
    _seed_old_snapshot(path)

    for _ in range(3):
        conn = connect(path)
        ensure_schema(conn)
        conn.close()

    conn = connect(path)
    assert conn.execute(f"SELECT COUNT(*) FROM {HISTORY_TABLE}").fetchone()[0] == 1
    conn.close()


def test_null_periods_are_stored_as_empty_strings(tmp_path):
    path = _db(tmp_path)
    upsert([_row("CHN", 1, "pv", count=0, period=(None, None), refreshed_at=10)], db_path=path)
    conn = connect(path)
    assert conn.execute(f"SELECT period_start, period_end FROM {HISTORY_TABLE}").fetchone() == ("", "")
    conn.close()


def test_upsert_of_no_rows_is_a_noop(tmp_path):
    path = _db(tmp_path)
    assert upsert([], db_path=path) == {"archived": 0, "history": 0, "current": 0}


def test_history_primary_key_rejects_a_duplicate_snapshot(tmp_path):
    path = _db(tmp_path)
    upsert([_row("GLB", 1, "pv", refreshed_at=42)], db_path=path)
    upsert([_row("GLB", 1, "pv", refreshed_at=42)], db_path=path)
    conn = connect(path)
    assert conn.execute(f"SELECT COUNT(*) FROM {HISTORY_TABLE}").fetchone()[0] == 1
    conn.close()
