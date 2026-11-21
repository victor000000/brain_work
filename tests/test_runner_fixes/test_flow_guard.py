"""FIX 5 (flow half): never re-POST an already-SUBMITTED alpha; ALREADY_SUBMITTED
is a success; a verified submit writes the check summary."""

import logging
from unittest.mock import MagicMock

import pytest

from runner.submit import flow
from storage.submission_requests import begin_request, needs_reconciliation, record_response
from tests.test_runner_fixes.helpers import FakeResponse


def _seed(conn, status):
    conn.execute(
        "INSERT INTO alpha_results "
        "(alpha_id, region, universe, delay, neutralization, status, template) "
        "VALUES ('A1', 'USA', 'TOP3000', 1, 'MARKET', ?, 'T')",
        (status,),
    )
    conn.commit()


def test_submitted_alpha_is_not_checked_or_reposted(monkeypatch, conn):
    _seed(conn, "SUBMITTED")
    monkeypatch.setattr(flow, "ensure_description", lambda *a: pytest.fail("patched description"))
    monkeypatch.setattr(flow, "try_submit", lambda *a: pytest.fail("re-POSTed a submitted alpha"))

    assert flow.check_and_submit(MagicMock(), conn, "A1") == "SUBMITTED"


def test_already_submitted_result_is_terminal_success(monkeypatch, conn, allowed_alpha_session):
    _seed(conn, "UNSUBMITTED")
    monkeypatch.setattr(flow, "ensure_description", lambda *a: None)
    monkeypatch.setattr(flow, "try_submit", lambda *a: (403, "ALREADY_SUBMITTED"))

    result = flow.check_and_submit(allowed_alpha_session, conn, "A1")

    assert result == "ALREADY_SUBMITTED"
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='A1'").fetchone()[0] == "SUBMITTED"


def test_verified_submit_records_check_summary(monkeypatch, conn, allowed_alpha_session):
    _seed(conn, "UNSUBMITTED")
    monkeypatch.setattr(flow, "ensure_description", lambda *a: None)
    monkeypatch.setattr(flow, "try_submit", lambda *a: (201, None))
    monkeypatch.setattr(flow, "verify_submission", lambda *a: "SUBMITTED")

    assert flow.check_and_submit(allowed_alpha_session, conn, "A1") == "SUBMITTED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='A1'").fetchone()[0] == 1
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='A1'").fetchone()[0] == "SUBMITTED"


def test_submitted_status_is_not_downgraded_by_later_rejection(monkeypatch, conn, allowed_alpha_session):
    _seed(conn, "UNSUBMITTED")
    monkeypatch.setattr(flow, "ensure_description", lambda *a: None)
    monkeypatch.setattr(flow, "try_submit", lambda *a: (403, "FAIL:1"))

    assert flow.check_and_submit(allowed_alpha_session, conn, "A1") == "FAIL:1"
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='A1'").fetchone()[0] == "REJECTED"


def test_the_fallback_log_line_survives_a_post_with_no_answer(monkeypatch, conn, caplog, allowed_alpha_session):
    """`status_code` is None when the POST never answered — `%d` eats the record.

    Both transport-failure returns of `check_via_submit` are `(None, None)`, and
    `%d` with None raises TypeError *inside* logging: the record is lost and a
    "--- Logging error ---" traceback lands in the log in its place. Measured
    2026-10-08 18:51: `omWlgVxk` took a read timeout on the POST, and this was
    the one line that would have said which path it took next.
    """
    _seed(conn, "UNSUBMITTED")
    monkeypatch.setattr(flow, "ensure_description", lambda *a: None)
    monkeypatch.setattr(flow, "try_submit", lambda *a: (None, None))
    monkeypatch.setattr(flow, "fallback_get_check", lambda *a: "CHECK_FAILED")

    with caplog.at_level(logging.DEBUG, logger="brain.check"):
        assert flow._do_check_and_submit(allowed_alpha_session, conn, "A1") == "CHECK_FAILED"

    assert "Fallback GET /check: A1 (status=None)" in caplog.text


@pytest.fixture
def read_only_submission(allowed_alpha_session, monkeypatch):
    def unexpected_write(*args):
        pytest.fail("A deferred or blocked expression reached a remote write")

    monkeypatch.setattr(flow, "ensure_description", unexpected_write)
    monkeypatch.setattr(flow, "try_submit", unexpected_write)
    return allowed_alpha_session


@pytest.mark.parametrize(
    "detail",
    [
        FakeResponse(200, json_data={"regular": {}}),
        FakeResponse(503, json_data={"regular": {"code": "rank(close)"}}),
        TimeoutError("detail unavailable"),
    ],
)
def test_unreadable_expression_defers_before_mutation(conn, read_only_submission, detail):
    _seed(conn, "UNSUBMITTED")
    read_only_submission.get.side_effect = [detail]

    assert flow.check_and_submit(read_only_submission, conn, "A1") == "CHECK_UNAVAILABLE"
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='A1'").fetchone() == (1,)
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='A1'").fetchone() == (0,)
    assert not needs_reconciliation(conn, "A1")


@pytest.mark.parametrize("http_status", [403, 429])
def test_retry_revalidates_scope_after_rejection(conn, read_only_submission, http_status):
    _seed(conn, "UNSUBMITTED")
    begin_request(conn, "A1")
    record_response(conn, "A1", http_status)
    read_only_submission.get.return_value.json.return_value = {"regular": {"code": "rank(pv87_eps_forward)"}}

    assert flow.check_and_submit(read_only_submission, conn, "A1") == "SCOPE_BLOCKED"
    read_only_submission.get.assert_called_once()
    assert conn.execute("SELECT state, http_status FROM submission_requests WHERE alpha_id='A1'").fetchone() == (
        "REJECTED",
        http_status,
    )
