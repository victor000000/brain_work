"""Shared helpers for the F3 selection-bias test package."""

import time

from core.db import connect, init_tables


def mem_conn():
    """Fresh in-memory DB with the simulation schema applied."""
    conn = connect(":memory:")
    init_tables(conn)
    return conn


def seed_priors(conn, rows):
    """Seed cell_priors rows.

    rows: list of (template, region, universe, delay, hit_weight, quarantined).
    Sets count=100, hits=10 across the board so coverage weights are equal.
    """
    now = int(time.time())
    for t, r, u, d, hw, q in rows:
        conn.execute(
            "INSERT INTO cell_priors "
            "(template, region, universe, delay, count, hits, hit_weight, "
            " quarantined, quarantined_at, refreshed_at) "
            "VALUES (?, ?, ?, ?, 100, 10, ?, ?, NULL, ?)",
            (t, r, u, d, hw, q, now),
        )
    conn.commit()


def make_template(name):
    """Build a no-op template fn whose __name__ matches `name`."""

    def _fn():
        pass

    _fn.__name__ = name
    return _fn
