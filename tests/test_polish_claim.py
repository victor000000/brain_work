"""Polish reservations release only on proof that no simulation was accepted."""

import random

import pytest

from runner.explore_helpers import polish
from runner.explore_helpers.polish_claim import release_unsubmitted_claim
from storage.store_checks import POLISH_MIN_PASSES, store_checks
from tests.test_polish_helpers import _alpha, _checks, conn

__all__ = ["conn"]


def _queued(conn, *, aid="A1", attempts=0, tried=""):
    _alpha(conn, aid=aid, expr=f"rank(close)+{len(aid)}")
    store_checks(conn, aid, _checks(POLISH_MIN_PASSES, 1))
    conn.execute("UPDATE polish_candidates SET attempts=?, tried=? WHERE alpha_id=?", (attempts, tried, aid))
    conn.commit()


def _state(conn, aid="A1"):
    return conn.execute("SELECT attempts, tried FROM polish_candidates WHERE alpha_id=?", (aid,)).fetchone()


def test_definite_rejection_restores_exact_attempt_and_tried_state(conn):
    _queued(conn, attempts=2, tried="FAST,SET:3:0.05")
    plan = polish.take_batch(conn, random.Random(0))
    assert _state(conn)[0] == 3

    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 1
    assert _state(conn) == (2, "FAST,SET:3:0.05")


@pytest.mark.parametrize("evidence", [False, None, "CONCURRENT", "BUDGET", 1])
def test_accepted_ambiguous_or_unclassified_outcome_does_not_release(conn, evidence):
    _queued(conn)
    plan = polish.take_batch(conn, random.Random(0))
    claimed = _state(conn)

    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=evidence) == 0
    assert _state(conn) == claimed


def test_a_definite_rejection_at_the_cap_restores_only_its_own_attempt(conn):
    _queued(conn, attempts=polish.POLISH_MAX_ATTEMPTS - 1)
    plan = polish.take_batch(conn, random.Random(0))
    assert _state(conn)[0] == polish.POLISH_MAX_ATTEMPTS
    assert polish.take_batch(conn, random.Random(0)) is None

    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 1
    assert _state(conn)[0] == polish.POLISH_MAX_ATTEMPTS - 1


@pytest.mark.parametrize("changed", [(2, "FAST"), (1, "later-variant")])
def test_stale_receipt_does_not_erase_later_attempt_or_variant(conn, changed):
    _queued(conn)
    plan = polish.take_batch(conn, random.Random(0))
    conn.execute("UPDATE polish_candidates SET attempts=?, tried=?", changed)

    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 0
    assert _state(conn) == changed


def test_repeated_release_cannot_refund_a_new_claim_with_identical_state(conn):
    _queued(conn)
    first = polish.take_batch(conn, random.Random(0))
    first_state = _state(conn)
    assert release_unsubmitted_claim(conn, first, definitely_unsubmitted=True) == 1

    second = polish.take_batch(conn, random.Random(0))
    assert _state(conn) == first_state
    assert release_unsubmitted_claim(conn, first, definitely_unsubmitted=True) == 0
    assert _state(conn) == first_state
    assert release_unsubmitted_claim(conn, second, definitely_unsubmitted=True) == 1


def test_changed_expression_with_same_id_is_not_refunded(conn):
    _queued(conn)
    plan = polish.take_batch(conn, random.Random(0))
    claimed = _state(conn)
    conn.execute("UPDATE polish_candidates SET expression='rank(volume)'")

    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 0
    assert _state(conn) == claimed


def test_multi_candidate_release_preserves_a_row_changed_after_claim(conn):
    _queued(conn)
    _queued(conn, aid="SECOND")
    plan = polish.take_batch(conn, random.Random(0))
    assert set(plan["alpha_ids"]) == {"A1", "SECOND"}
    conn.execute("UPDATE polish_candidates SET attempts=2, tried='later-variant' WHERE alpha_id='SECOND'")

    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 1
    assert _state(conn) == (0, "")
    assert _state(conn, "SECOND") == (2, "later-variant")


def test_stale_receipt_stays_settled_if_row_later_matches_again(conn):
    _queued(conn)
    plan = polish.take_batch(conn, random.Random(0))
    claimed = _state(conn)
    conn.execute("UPDATE polish_candidates SET attempts=2, tried='later-variant'")
    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 0

    conn.execute("UPDATE polish_candidates SET attempts=?, tried=?", claimed)
    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 0
    assert _state(conn) == claimed


@pytest.mark.parametrize("plan", [None, {}, {"expressions": ["rank(close)"]}])
def test_missing_receipt_does_not_release_anything(conn, plan):
    _queued(conn, attempts=3, tried="FAST")
    assert release_unsubmitted_claim(conn, plan, definitely_unsubmitted=True) == 0
    assert _state(conn) == (3, "FAST")
