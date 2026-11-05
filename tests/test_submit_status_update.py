"""Tests for alpha_results.status updates after check_and_submit."""

from core.db import connect, init_tables
from runner.submit import _result_to_status, _update_alpha_status


def test_result_to_status_terminal_outcomes():
    assert _result_to_status("SUBMITTED") == "SUBMITTED"
    assert _result_to_status("THROTTLED") == "THROTTLED"
    assert _result_to_status("FAIL:1") == "REJECTED"
    assert _result_to_status("FAIL:7") == "REJECTED"


def test_result_to_status_transient_outcomes():
    assert _result_to_status("NOT_SUBMITTED") is None
    assert _result_to_status("VERIFY_FAILED") is None
    assert _result_to_status("CHECK_FAILED") is None
    assert _result_to_status("PASS_BUT_SUBMIT_FAILED") is None
    assert _result_to_status("CORR_FAIL") is None


def _make_alpha_results():
    conn = connect(":memory:")
    init_tables(conn)
    conn.executemany(
        "INSERT INTO alpha_results (alpha_id, status) VALUES (?, ?)",
        [("a1", "UNSUBMITTED"), ("a2", "UNSUBMITTED"), ("a3", "UNSUBMITTED")],
    )
    conn.commit()
    return conn


def test_update_alpha_status_submitted():
    conn = _make_alpha_results()
    _update_alpha_status(conn, "a1", "SUBMITTED")
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "SUBMITTED"


def test_update_alpha_status_rejected():
    conn = _make_alpha_results()
    _update_alpha_status(conn, "a2", "FAIL:5")
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a2'").fetchone()[0] == "REJECTED"


def test_update_alpha_status_transient_no_op():
    """Transient outcomes leave status as UNSUBMITTED so the row is retry-eligible."""
    conn = _make_alpha_results()
    for outcome in ("NOT_SUBMITTED", "VERIFY_FAILED", "CHECK_FAILED"):
        _update_alpha_status(conn, "a3", outcome)
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a3'").fetchone()[0] == "UNSUBMITTED"


def test_update_alpha_status_throttled():
    conn = _make_alpha_results()
    _update_alpha_status(conn, "a1", "THROTTLED")
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "THROTTLED"
