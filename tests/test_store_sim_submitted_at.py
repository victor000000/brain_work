"""`simulations.submitted_at`: populated from 2026-10-12, NULL before it.

The column was in the schema from the start and written by nothing — all
322,047 rows read NULL on 2026-10-12 — so no per-simulation latency could be
measured from the database, and "is this shape slow?" had to be argued from
per-batch progress in the poll logs. These pin the two halves: rows written
with a submission time carry it, rows written without one keep the NULL rather
than a plausible-looking wrong value.
"""

import calendar
import time

from core.db import connect
from storage.store_sim import store_sim, utc_text


def _conn():
    conn = connect(":memory:")
    conn.executescript("""
        CREATE TABLE simulations (
            sim_id TEXT PRIMARY KEY, parent_id TEXT, batch_idx INTEGER, expression TEXT,
            region TEXT, universe TEXT, delay INTEGER, status TEXT, alpha_id TEXT,
            error_message TEXT, submitted_at TEXT, completed_at TEXT, raw_settings TEXT
        );
    """)
    return conn


def test_submitted_at_is_written_when_given():
    conn = _conn()
    store_sim(
        conn,
        "child1",
        "parent",
        7,
        "rank(close)",
        "USA",
        "TOP3000",
        1,
        "COMPLETE",
        "abc",
        None,
        {"region": "USA"},
        "2026-10-12 13:00:00 UTC",
        submitted_at="2026-10-12 12:00:00 UTC",
    )
    row = conn.execute("SELECT submitted_at, completed_at FROM simulations WHERE sim_id='child1'").fetchone()
    assert row == ("2026-10-12 12:00:00 UTC", "2026-10-12 13:00:00 UTC")


def test_submitted_at_stays_null_without_one():
    conn = _conn()
    store_sim(
        conn,
        "p1",
        None,
        7,
        "[]",
        "USA",
        "TOP3000",
        1,
        "SUBMITTED",
        None,
        None,
        {"region": "USA"},
        "2026-10-12 12:00:00 UTC",
    )
    assert conn.execute("SELECT submitted_at FROM simulations WHERE sim_id='p1'").fetchone()[0] is None


def test_utc_text_formats_an_epoch_and_passes_none_through():
    epoch = calendar.timegm(time.strptime("2026-10-12 12:00:00", "%Y-%m-%d %H:%M:%S"))
    assert utc_text(epoch) == "2026-10-12 12:00:00 UTC"
    assert utc_text(None) is None
    assert utc_text(0.0) == "1970-01-01 00:00:00 UTC"
