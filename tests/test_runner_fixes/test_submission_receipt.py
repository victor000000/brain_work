"""Confirmed platform dates survive reporting without changing submit decisions."""

import json
from unittest.mock import MagicMock

import pytest

from runner import verify_submit
from tests.test_runner_fixes.helpers import FakeResponse


def seed(conn, raw):
    conn.execute("INSERT INTO alpha_results(alpha_id,status,raw_json) VALUES ('R1','UNSUBMITTED',?)", (raw,))
    conn.commit()


def test_confirmed_date_is_persisted_without_losing_alpha_metrics(conn):
    original = {"is": {"sharpe": 2.4}, "regular": {"code": "rank(close)"}, "status": "UNSUBMITTED"}
    seed(conn, json.dumps(original))
    session = MagicMock()
    submitted = "2026-10-17T03:21:00-04:00"
    session.get.return_value = FakeResponse(200, json_data={"dateSubmitted": submitted, "status": "ACTIVE"})

    assert verify_submit.verify_submission(session, conn, "R1") == "SUBMITTED"

    raw, local_status = conn.execute("SELECT raw_json,status FROM alpha_results WHERE alpha_id='R1'").fetchone()
    stored = json.loads(raw)
    assert stored == {**original, "dateSubmitted": submitted, "status": "ACTIVE"}
    assert local_status == "UNSUBMITTED"  # The normal outcome transaction owns this transition.
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals WHERE alpha_id='R1'").fetchone()[0] == 0


@pytest.mark.parametrize("http,expected", [(200, "PENDING"), (503, "VERIFY_FAILED")])
def test_undecided_verification_does_not_invent_a_receipt(conn, monkeypatch, http, expected):
    original = {"dateSubmitted": None, "status": "UNSUBMITTED", "is": {"sharpe": 2.4}}
    seed(conn, json.dumps(original))
    monkeypatch.setattr(verify_submit, "VERIFY_MAX_WAIT_SEC", 0)
    session = MagicMock()
    session.get.return_value = FakeResponse(http, json_data={"dateSubmitted": None})

    assert verify_submit.verify_submission(session, conn, "R1") == expected
    raw = conn.execute("SELECT raw_json FROM alpha_results WHERE alpha_id='R1'").fetchone()[0]
    assert json.loads(raw) == original
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='R1'").fetchone()[0] == 1


def test_receipt_write_failure_does_not_turn_confirmed_acceptance_into_a_retry(conn):
    seed(conn, "corrupt legacy JSON")
    session = MagicMock()
    session.get.return_value = FakeResponse(
        200, json_data={"dateSubmitted": "2026-10-17T07:00:00Z", "status": "ACTIVE"}
    )

    assert verify_submit.verify_submission(session, conn, "R1") == "SUBMITTED"
    assert conn.execute("SELECT raw_json FROM alpha_results WHERE alpha_id='R1'").fetchone()[0] == "corrupt legacy JSON"
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals WHERE alpha_id='R1'").fetchone()[0] == 0
