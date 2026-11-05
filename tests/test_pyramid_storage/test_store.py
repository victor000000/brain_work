"""store_pyramid_state — insert, snapshot semantics, rollback."""

from core.db import IntegrityError
from tests.test_pyramid_storage.conftest import mem_conn


def test_store_pyramid_state_inserts_rows():
    """One refresh writes len(multipliers) + len(alpha_counts) rows under one fetched_at."""
    from download.pyramid import store_pyramid_state

    conn = mem_conn()
    multipliers = [
        {"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.6},
        {"category": "fundamental", "region": "USA", "delay": 1, "multiplier": 1.4},
    ]
    alpha_counts = [
        {"category": "pv", "region": "USA", "delay": 0, "alpha_count": 12},
        {"category": "fundamental", "region": "USA", "delay": 1, "alpha_count": 0},
    ]
    store_pyramid_state(conn, multipliers, alpha_counts, fetched_at=1700000000)

    m_rows = conn.execute(
        "SELECT category, region, delay, multiplier, fetched_at FROM pyramid_multipliers ORDER BY category"
    ).fetchall()
    assert m_rows == [
        ("fundamental", "USA", 1, 1.4, 1700000000),
        ("pv", "USA", 0, 1.6, 1700000000),
    ]
    a_rows = conn.execute(
        "SELECT category, region, delay, alpha_count, fetched_at FROM pyramid_alpha_counts ORDER BY category"
    ).fetchall()
    assert a_rows == [
        ("fundamental", "USA", 1, 0, 1700000000),
        ("pv", "USA", 0, 12, 1700000000),
    ]


def test_store_pyramid_state_snapshot_semantics():
    """Two refreshes with different fetched_at append rows; both snapshots retained."""
    from download.pyramid import store_pyramid_state

    conn = mem_conn()
    multipliers = [{"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.6}]
    alpha_counts = [{"category": "pv", "region": "USA", "delay": 0, "alpha_count": 0}]

    store_pyramid_state(conn, multipliers, alpha_counts, fetched_at=1000)
    multipliers2 = [{"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.7}]
    alpha_counts2 = [{"category": "pv", "region": "USA", "delay": 0, "alpha_count": 5}]
    store_pyramid_state(conn, multipliers2, alpha_counts2, fetched_at=2000)

    assert conn.execute("SELECT COUNT(*) FROM pyramid_multipliers").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM pyramid_alpha_counts").fetchone()[0] == 2
    m_times = sorted(r[0] for r in conn.execute("SELECT DISTINCT fetched_at FROM pyramid_multipliers"))
    assert m_times == [1000, 2000]


def test_store_pyramid_state_rollback_on_collision():
    """If second executemany fails with IntegrityError, first executemany's writes
    are rolled back so neither table sees the partial snapshot."""
    from download.pyramid import store_pyramid_state

    conn = mem_conn()
    multipliers = [{"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.6}]
    alpha_counts = [{"category": "pv", "region": "USA", "delay": 0, "alpha_count": 0}]
    store_pyramid_state(conn, multipliers, alpha_counts, fetched_at=1000)

    # Same fetched_at + same alpha_counts cell -> PK collision in pyramid_alpha_counts.
    multipliers2 = [{"category": "fundamental", "region": "USA", "delay": 1, "multiplier": 1.4}]
    alpha_counts2 = [{"category": "pv", "region": "USA", "delay": 0, "alpha_count": 99}]
    try:
        store_pyramid_state(conn, multipliers2, alpha_counts2, fetched_at=1000)
        raise AssertionError("expected IntegrityError")
    except IntegrityError:
        pass

    # The new multipliers row must NOT have been persisted (rollback).
    new_mult = conn.execute("SELECT COUNT(*) FROM pyramid_multipliers WHERE category='fundamental'").fetchone()[0]
    assert new_mult == 0, "multipliers row should have been rolled back"
    assert conn.execute("SELECT COUNT(*) FROM pyramid_multipliers").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM pyramid_alpha_counts").fetchone()[0] == 1
