"""A fresh undecided verdict must supersede a previous checked-summary marker."""

from unittest.mock import MagicMock

import pytest

from checker.auto_check_alpha import _check_alpha
from checker.auto_check_queue import _select_candidates
from runner import submit_checks
from runner.submit import flow
from storage.store_checks import store_checks
from tests.test_runner_fixes.auto_check_helpers import _seed

OLD_CHECKS = [
    {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.0},
    {"name": "PROD_CORRELATION", "result": "FAIL", "limit": 0.7, "value": 0.84},
]
UNDECIDED_CHECKS = [
    {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.0},
    {"name": "CLUSTER_TEST", "result": "ERROR"},
    {"name": "PROD_CORRELATION", "result": "PENDING"},
    {"name": "SELF_CORRELATION", "result": "PENDING"},
]


def _previously_checked(conn, alpha_id="A1", status="THROTTLED"):
    _seed(conn, alpha_id, 2.0, status=status)
    store_checks(conn, alpha_id, OLD_CHECKS)
    conn.execute("UPDATE alpha_check_summary SET checked_at='2026-10-03 10:29:00 UTC' WHERE alpha_id=?", (alpha_id,))
    conn.commit()


def _summary(conn, alpha_id="A1"):
    return conn.execute("SELECT fail_count FROM alpha_check_summary WHERE alpha_id=?", (alpha_id,)).fetchone()


def test_explicit_no_summary_removes_previous_decision_but_keeps_failure_history(conn):
    _previously_checked(conn)
    historical = conn.execute("SELECT * FROM check_failures WHERE alpha_id='A1'").fetchall()

    store_checks(conn, "A1", UNDECIDED_CHECKS, write_summary=False)

    assert _summary(conn) is None
    assert conn.execute("SELECT * FROM check_failures WHERE alpha_id='A1'").fetchall() == historical
    assert conn.execute(
        "SELECT result FROM submission_checks WHERE alpha_id='A1' AND check_name='PROD_CORRELATION'"
    ).fetchone() == ("PENDING",)
    assert [aid for aid, _ in _select_candidates(conn, 10)] == ["A1"]


@pytest.mark.parametrize("quota", ["REGULAR_SUBMISSION", "POWER_POOL_SUBMISSION"])
def test_quota_only_no_summary_also_removes_previous_decision(conn, quota):
    _previously_checked(conn)
    store_checks(conn, "A1", [{"name": quota, "result": "FAIL", "limit": 4, "value": 4}])

    assert _summary(conn) is None
    assert [aid for aid, _ in _select_candidates(conn, 10)] == ["A1"]
    assert {row[0] for row in conn.execute("SELECT check_name FROM check_failures WHERE alpha_id='A1'").fetchall()} == {
        "PROD_CORRELATION",
        quota,
    }


@pytest.mark.parametrize("blocked", ["pending", "quota"])
def test_real_check_pipeline_returns_previously_checked_alpha_to_retry_queue(conn, monkeypatch, blocked):
    _previously_checked(conn)
    _seed(conn, "FRESH", 1.7)
    assert [aid for aid, _ in _select_candidates(conn, 10)] == ["FRESH"]
    newest = (
        UNDECIDED_CHECKS
        if blocked == "pending"
        else [{"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4, "value": 4}]
    )
    monkeypatch.setattr(flow, "ensure_description", lambda *args: None)
    monkeypatch.setattr(submit_checks, "check_via_submit", lambda session, aid: (403, newest))

    _check_alpha(
        None,
        conn,
        "A1",
        2.0,
        check_via_get=lambda session, aid: UNDECIDED_CHECKS,
        check_and_submit=flow.check_and_submit,
    )

    assert _summary(conn) is None
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='A1'").fetchone() == ("THROTTLED",)
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='A1'").fetchone() == (1,)
    assert [aid for aid, _ in _select_candidates(conn, 10)] == ["FRESH", "A1"]
    # Removing a stale decision must not remove the independent retry backoff.
    conn.execute("UPDATE check_deferrals SET attempts=3 WHERE alpha_id='A1'")
    assert [aid for aid, _ in _select_candidates(conn, 10)] == ["FRESH"]


def test_a_current_real_failure_still_replaces_the_summary(conn):
    _previously_checked(conn)
    store_checks(
        conn,
        "A1",
        [
            {"name": "PROD_CORRELATION", "result": "FAIL", "limit": 0.7, "value": 0.82},
            {"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4, "value": 4},
        ],
    )

    assert _summary(conn) == (2,)
    assert _select_candidates(conn, 10) == []
    assert conn.execute(
        "SELECT seen_count,actual_val FROM check_failures WHERE alpha_id='A1' AND check_name='PROD_CORRELATION'"
    ).fetchone() == (2, "0.82")


def test_no_summary_never_reopens_a_terminal_submitted_alpha(conn):
    _previously_checked(conn, status="SUBMITTED")
    store_checks(conn, "A1", UNDECIDED_CHECKS, write_summary=False)

    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='A1'").fetchone() == ("SUBMITTED",)
    assert _select_candidates(conn, 10) == []
    session = MagicMock()
    assert flow.check_and_submit(session, conn, "A1") == "SUBMITTED"
    session.post.assert_not_called()
