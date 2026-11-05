"""One-time backfill: for every SUBMITTED alpha without an incremented
submission_outcomes row, bump the counter via _record_outcome."""

import pytest

from core.db import connect, init_tables


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_tables(c)
    c.executemany(
        "INSERT INTO alpha_results "
        "(alpha_id, template, region, universe, delay, neutralization, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("X1", "ts_backfill_negmean", "CHN", "TOP2000U", 0, "NONE", "SUBMITTED"),
            ("X2", "scale_rank_zscore", "EUR", "TOP2500", 0, "FAST", "SUBMITTED"),
            ("X3", "power_ratio", "USA", "TOP3000", 1, "SLOW_AND_FAST", "REJECTED"),
        ],
    )
    c.commit()
    yield c
    c.close()


def test_backfill_bumps_submitted_for_all_submitted_alphas(conn):
    from tools.backfill_submission_outcomes import run_backfill

    n = run_backfill(conn)
    assert n == 2  # only the two SUBMITTED rows got bumped
    submitted_total = conn.execute("SELECT SUM(submitted) FROM submission_outcomes").fetchone()[0]
    assert submitted_total == 2


def test_backfill_idempotent(conn):
    """Running backfill twice should not double-bump."""
    from tools.backfill_submission_outcomes import run_backfill

    run_backfill(conn)
    run_backfill(conn)
    submitted_total = conn.execute("SELECT SUM(submitted) FROM submission_outcomes").fetchone()[0]
    # Backfill uses delta=owed-already_recorded, so second run is a no-op.
    assert submitted_total == 2
