"""Builders shared by the refresh_pyramid_targets persistence tests."""

from core.db import connect


def _db(tmp_path):
    return str(tmp_path / "targets.db")


def _row(region, delay, category, count=0, period=("2026-04-01", "2026-06-30"), refreshed_at=1000):
    multiplier = 1.5
    gap = max(0, 3 - count)
    return {
        "region": region,
        "delay": delay,
        "category": category,
        "alpha_count": count,
        "multiplier": multiplier,
        "gap_to_3": gap,
        "score": gap * multiplier,
        "period_start": period[0],
        "period_end": period[1],
        "refreshed_at": refreshed_at,
    }


def _seed_old_snapshot(path):
    """A DB in the pre-fix shape: current table only, holding Q2 rows."""
    conn = connect(path)
    conn.execute("""
        CREATE TABLE pyramid_targets (
            region TEXT NOT NULL, delay INTEGER NOT NULL, category TEXT NOT NULL,
            alpha_count INTEGER NOT NULL DEFAULT 0, multiplier REAL NOT NULL DEFAULT 1.0,
            gap_to_3 INTEGER NOT NULL DEFAULT 3, score REAL NOT NULL DEFAULT 0,
            period_start TEXT, period_end TEXT, refreshed_at INTEGER NOT NULL,
            PRIMARY KEY (region, delay, category)
        )
    """)
    conn.execute(
        "INSERT INTO pyramid_targets VALUES ('USA', 1, 'pv', 1, 1.7, 2, 17.0, '2026-04-01', '2026-06-30', 1779503467)"
    )
    conn.commit()
    conn.close()
