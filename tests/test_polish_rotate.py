"""Near-miss polishing: batches rotate across cells and candidates."""

import random

from runner.explore_helpers import polish
from storage.store_checks import POLISH_MIN_PASSES, store_checks
from tests.test_polish_helpers import _alpha, _checks, conn

__all__ = ["conn"]

# --------------------------------------------------------------- rotation ---


def test_a_small_cell_is_not_starved_by_a_large_one(conn):
    """The largest cell must not win every batch forever.

    Picking `max(cell, key=len)` starved every other cell permanently: 110 of
    the 124 polish batches on 2026-10-05/06 went to HKG/TOP800/d1, while
    one-fail alphas elsewhere were never re-run at all.
    """
    for i in range(6):
        _alpha(conn, aid=f"H{i}", region="HKG", expr=f"rank(close)+{i}")
        store_checks(conn, f"H{i}", _checks(POLISH_MIN_PASSES, 1))
    _alpha(conn, aid="U1", region="USA", expr="rank(volume)")
    store_checks(conn, "U1", _checks(POLISH_MIN_PASSES, 1))
    # The big cell has already had its turns; the untouched one has not.
    conn.execute("UPDATE polish_candidates SET attempts = 2 WHERE region = 'HKG'")

    plan = polish.take_batch(conn, random.Random(0))

    assert plan["region"] == "USA", "the untouched small cell never got a turn"


def test_the_large_cell_comes_back_once_the_small_ones_are_worked(conn):
    """Rotation, not exclusion: the average-attempts key must let it return."""
    for i in range(6):
        _alpha(conn, aid=f"H{i}", region="HKG", expr=f"rank(close)+{i}")
        store_checks(conn, f"H{i}", _checks(POLISH_MIN_PASSES, 1))
    _alpha(conn, aid="U1", region="USA", expr="rank(volume)")
    store_checks(conn, "U1", _checks(POLISH_MIN_PASSES, 1))
    conn.execute("UPDATE polish_candidates SET attempts = 1 WHERE region = 'USA'")

    plan = polish.take_batch(conn, random.Random(0))

    assert plan["region"] == "HKG", "a total-based key would lock the big cell out forever"


def test_successive_batches_rotate_through_the_queue(conn):
    """Coverage spreads across candidates before any is re-run.

    Ordering by age alone handed the same oldest few to every batch.
    """
    ids = [f"A{i}" for i in range(polish.POLISH_MAX_EXPRS * 2)]
    for aid in ids:
        _alpha(conn, aid=aid, expr=f"rank(close)+{aid}")
        store_checks(conn, aid, _checks(POLISH_MIN_PASSES, 1))

    first = polish.take_batch(conn, random.Random(0))["alpha_ids"]
    second = polish.take_batch(conn, random.Random(0))["alpha_ids"]
    assert set(first).isdisjoint(second), (first, second)
    # ...and the third batch comes back to the first group, now least-attempted.
    third = polish.take_batch(conn, random.Random(0))["alpha_ids"]
    assert set(third) == set(first)
