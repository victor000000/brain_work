"""get_current_pyramid_state — returns rows from the latest snapshot only."""

from tests.test_pyramid_storage.conftest import mem_conn


def test_get_current_pyramid_state_returns_latest_only():
    """Two snapshots stored; helper returns only rows from the most recent fetched_at."""
    from download.pyramid import get_current_pyramid_state, store_pyramid_state

    conn = mem_conn()
    # Older snapshot.
    store_pyramid_state(
        conn,
        [{"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.5}],
        [{"category": "pv", "region": "USA", "delay": 0, "alpha_count": 3}],
        fetched_at=1000,
    )
    # Newer snapshot, two cells.
    store_pyramid_state(
        conn,
        [
            {"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.6},
            {"category": "fundamental", "region": "USA", "delay": 1, "multiplier": 1.4},
        ],
        [
            {"category": "pv", "region": "USA", "delay": 0, "alpha_count": 5},
            {"category": "fundamental", "region": "USA", "delay": 1, "alpha_count": 0},
        ],
        fetched_at=2000,
    )

    rows = get_current_pyramid_state(conn)
    # Sorted by multiplier DESC then alpha_count ASC.
    assert rows == [
        {"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.6, "alpha_count": 5, "fetched_at": 2000},
        {
            "category": "fundamental",
            "region": "USA",
            "delay": 1,
            "multiplier": 1.4,
            "alpha_count": 0,
            "fetched_at": 2000,
        },
    ]
