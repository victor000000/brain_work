"""FIX 4 (+3): a FAILED/empty parent is a terminal error, and only a real
result counts as success."""

import time

from runner import poll_batch as pb
from tests.test_runner_fixes.helpers import FakeResponse, batch_info
from tests.test_runner_fixes.test_poll_batch_errors_helpers import session_for, stored_parent  # noqa: F401


def test_empty_body_records_terminal_error(conn):
    """Past the minimum age, two consecutive no-result reads call it dead."""
    info = batch_info(submitted_at=time.time() - 300)
    first = pb.poll_batch(session_for(FakeResponse(200, json_data={})), info, conn)
    assert first is False  # transient: re-poll

    done = pb.poll_batch(session_for(FakeResponse(200, json_data={})), info, conn)
    assert done is True
    row = conn.execute("SELECT status, error_message FROM simulations WHERE sim_id='P1'").fetchone()
    assert row[0] == "ERROR"
    assert row[1]
    err = conn.execute("SELECT error_message FROM sim_errors WHERE sim_id='P1'").fetchall()
    assert len(err) == 1


def test_fail_status_records_error(conn):
    info = batch_info(submitted_at=time.time() - 300)
    resp = FakeResponse(200, json_data={"status": "FAIL", "message": "division by zero"})
    first = pb.poll_batch(session_for(resp), info, conn)
    assert first is False  # transient body: re-poll before writing it off

    done = pb.poll_batch(session_for(resp), info, conn)
    assert done is True
    row = conn.execute("SELECT status, error_message FROM simulations WHERE sim_id='P1'").fetchone()
    assert row[0] == "ERROR"
    assert "division" in row[1]


def test_success_requires_a_result(monkeypatch, conn):
    info = batch_info()
    monkeypatch.setattr(pb, "handle_single", lambda *a: (1, 0, True))
    resp = FakeResponse(200, json_data={"alpha": "A1", "status": "COMPLETE"})

    done = pb.poll_batch(session_for(resp), info, conn)

    assert done is True
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "COMPLETE"


def test_young_batch_is_never_written_off(conn):
    """A freshly submitted batch returns a no-result body while its children
    are still being created; it must keep being polled regardless of strikes."""
    info = batch_info()  # age ~0
    for _ in range(5):
        assert pb.poll_batch(session_for(FakeResponse(200, json_data={"status": "ERROR"})), info, conn) is False
    row = conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()
    assert row[0] == "SUBMITTED"
