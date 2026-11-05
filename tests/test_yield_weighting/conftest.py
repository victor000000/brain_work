"""Shared in-memory DB factory for the yield-weighting tests."""

from core.db import connect


def make_yield_db():
    """In-memory DB seeded with three configs of varying yield."""
    conn = connect(":memory:")
    conn.execute("""
        CREATE TABLE alpha_results (
            neutralization TEXT, decay INT, truncation REAL,
            region TEXT, universe TEXT, delay INT,
            is_sharpe REAL, raw_json TEXT, pyramid_categories TEXT
        )
    """)
    rows = []
    # pyramid_categories is required and must be pv/option for a row to count.
    # IND: 100 sims, 12 winners.
    rows += [("MARKET", 4, 0.08, "IND", "TOP500", 1, 1.5, None, '["pv"]') for _ in range(12)]
    rows += [("MARKET", 4, 0.08, "IND", "TOP500", 1, 0.2, None, '["pv"]') for _ in range(88)]
    # USA: 100 sims, 2 winners.
    rows += [("MARKET", 4, 0.08, "USA", "TOP3000", 1, 1.2, None, '["pv"]') for _ in range(2)]
    rows += [("MARKET", 4, 0.08, "USA", "TOP3000", 1, 0.1, None, '["pv"]') for _ in range(98)]
    conn.executemany("INSERT INTO alpha_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    return conn
