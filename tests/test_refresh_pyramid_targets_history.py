"""refresh_pyramid_targets history: refreshes append, never replace.

The old upsert replaced the only stored snapshot on (region, delay, category):
a Q3 refresh destroyed the Q2 rows. These tests pin the history table's
append-only behaviour.
"""

import pytest

from core.db import connect
from tests.test_refresh_pyramid_targets_helpers import _db, _row, _seed_old_snapshot
from tools.refresh_pyramid_targets.persist import HISTORY_TABLE, upsert


def test_refresh_for_a_new_period_keeps_the_old_period(tmp_path):
    """The exact defect: refreshing Q3 must not destroy the Q2 snapshot."""
    path = _db(tmp_path)
    _seed_old_snapshot(path)

    q3 = _row("USA", 1, "pv", count=4, period=("2026-07-01", "2026-09-30"), refreshed_at=2_000_000_000)
    upsert([q3], db_path=path)

    conn = connect(path)
    periods = dict(
        conn.execute(
            f"SELECT period_start, alpha_count FROM {HISTORY_TABLE} WHERE region='USA' AND category='pv'"
        ).fetchall()
    )
    assert periods == {"2026-04-01": 1, "2026-07-01": 4}
    # the current table follows the newest refresh
    assert conn.execute(
        "SELECT alpha_count, period_start FROM pyramid_targets WHERE region='USA' AND category='pv'"
    ).fetchone() == (4, "2026-07-01")
    conn.close()


def test_each_refresh_appends_a_history_row(tmp_path):
    path = _db(tmp_path)
    upsert([_row("EUR", 0, "pv", count=2, refreshed_at=100)], db_path=path)
    upsert([_row("EUR", 0, "pv", count=3, refreshed_at=200)], db_path=path)

    conn = connect(path)
    rows = conn.execute(
        f"SELECT alpha_count, refreshed_at FROM {HISTORY_TABLE} WHERE region='EUR' ORDER BY refreshed_at"
    ).fetchall()
    assert rows == [(2, 100), (3, 200)]
    conn.close()


def test_an_older_refresh_does_not_clobber_the_current_snapshot(tmp_path):
    path = _db(tmp_path)
    upsert([_row("ASI", 1, "pv", count=4, refreshed_at=2000)], db_path=path)
    upsert([_row("ASI", 1, "pv", count=0, refreshed_at=1000)], db_path=path)

    conn = connect(path)
    assert conn.execute("SELECT alpha_count, refreshed_at FROM pyramid_targets").fetchone() == (4, 2000)
    # ...but it is still recorded in history, which is append-only
    assert conn.execute(f"SELECT COUNT(*) FROM {HISTORY_TABLE}").fetchone()[0] == 2
    conn.close()


@pytest.mark.parametrize("count", [0, 1, 2, 3, 5])
def test_history_retains_counts_above_the_gap_cap(tmp_path, count):
    path = _db(tmp_path)
    upsert([_row("USA", 0, "option", count=count, refreshed_at=7)], db_path=path)
    conn = connect(path)
    assert conn.execute(f"SELECT alpha_count FROM {HISTORY_TABLE}").fetchone()[0] == count
    conn.close()
