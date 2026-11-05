"""A polish candidate is never simulated twice under the same neutralization.

Polish holds the expression and the cell fixed and varies only the risk model,
so re-running a neutralization the candidate has already been simulated with
produces an *identical* simulation. Measured 2026-10-06/07: 207 duplicate
simulations in a day (8.9% of all alphas stored), 50 of them polish re-runs,
one candidate four times. The `tried` column is the record that prevents it.
"""

import random

from runner.explore_helpers import polish
from runner.settings_factory import ALLOWED_NEUT_BY_REGION
from storage.store_checks import POLISH_MIN_PASSES, store_checks
from tests.test_polish_helpers import _alpha, _checks, conn

__all__ = ["conn"]

HKG = sorted(ALLOWED_NEUT_BY_REGION["HKG"])


def test_the_chosen_neutralization_is_recorded(conn):
    """Without the record the next attempt cannot know it is repeating."""
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    plan = polish.take_batch(conn, random.Random(0))
    tried = conn.execute("SELECT tried FROM polish_candidates").fetchone()[0]
    assert tried == plan["neutralization"]


def test_the_record_accumulates_across_attempts(conn):
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    seen = set()
    for seed in range(3):
        plan = polish.take_batch(conn, random.Random(seed))
        assert plan is not None
        seen.add(plan["neutralization"])
    tried = conn.execute("SELECT tried FROM polish_candidates").fetchone()[0]
    assert set(tried.split(",")) == seen
    assert len(seen) == 3, "a second attempt repeated an already-simulated neutralization"


def test_every_remaining_neutralization_is_excluded(conn):
    """Exhausting the list retires the candidate instead of repeating one."""
    _alpha(conn, neut="SLOW")
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    # Everything HKG allows except one, plus the original, is spent.
    left = HKG[-1]
    conn.execute("UPDATE polish_candidates SET tried = ?", (",".join(HKG[:-1]),))
    plan = polish.take_batch(conn, random.Random(0))
    assert plan["neutralization"] == left

    conn.execute("UPDATE polish_candidates SET tried = ?", (",".join(HKG),))
    assert polish.take_batch(conn, random.Random(0)) is None


def test_the_exclusion_covers_the_whole_batch(conn):
    """One batch runs one neutralization, so it must be new for all of them.

    Only the first candidate's history was consulted, so a later one could be
    re-simulated under a neutralization it had already been run with.
    """
    _alpha(conn, aid="A1")
    _alpha(conn, aid="B1", expr="rank(volume)")
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    store_checks(conn, "B1", _checks(POLISH_MIN_PASSES, 1))
    # B1 has seen everything but one; A1 has seen nothing. The union forces the
    # remaining one, where A1's history alone would have left the pick free.
    left = HKG[-1]
    conn.execute("UPDATE polish_candidates SET tried = ? WHERE alpha_id = 'B1'", (",".join(HKG[:-1]),))

    plan = polish.take_batch(conn, random.Random(0))
    assert sorted(plan["alpha_ids"]) == ["A1", "B1"]
    assert plan["neutralization"] == left
    # Both were charged the variant they were actually run under.
    rows = conn.execute("SELECT alpha_id, tried FROM polish_candidates ORDER BY alpha_id").fetchall()
    assert [r[1] for r in rows] == [left, ",".join(HKG[:-1]) + "," + left]
