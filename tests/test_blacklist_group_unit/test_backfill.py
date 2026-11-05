"""backfill_blacklist — insert offenders, idempotency, preserve other reasons."""

from download.blacklist_group_unit import backfill_blacklist
from tests.test_blacklist_group_unit.conftest import add_blacklist_table, make_test_conn


def test_backfill_inserts_offenders():
    conn = make_test_conn()
    add_blacklist_table(conn)
    inserted = backfill_blacklist(conn)
    assert inserted >= 1
    rows = conn.execute("SELECT field_id, region, reason FROM field_blacklist ORDER BY field_id, region").fetchall()
    assert ("group_id", "CHN", "group_unit") in rows
    assert ("group_id", "USA", "group_unit") in rows


def test_backfill_is_idempotent():
    """Running backfill twice does not duplicate rows."""
    conn = make_test_conn()
    add_blacklist_table(conn)
    first = backfill_blacklist(conn)
    second = backfill_blacklist(conn)
    assert second == 0
    count = conn.execute("SELECT COUNT(*) FROM field_blacklist").fetchone()[0]
    assert count == first


def test_backfill_preserves_other_reasons():
    """Existing field_blacklist rows with different reasons are untouched."""
    conn = make_test_conn()
    add_blacklist_table(conn)
    conn.execute(
        "INSERT INTO field_blacklist VALUES (?, ?, ?)",
        ("price", "USA", "lookback"),
    )
    backfill_blacklist(conn)
    assert (
        conn.execute(
            "SELECT 1 FROM field_blacklist WHERE field_id='price' AND region='USA' AND reason='lookback'"
        ).fetchone()
        is not None
    )
