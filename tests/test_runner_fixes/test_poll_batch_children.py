"""FIX 4: a parent that lists children is complete only when they are fetched."""

import time

from runner import poll_batch as pb
from tests.test_runner_fixes.helpers import FakeResponse, batch_info
from tests.test_runner_fixes.test_poll_batch_errors_helpers import session_for, stored_parent  # noqa: F401


def test_incomplete_children_keep_batch_in_flight(monkeypatch, conn):
    info = batch_info()
    monkeypatch.setattr(pb, "handle_children", lambda *a: (1, 1, False))
    resp = FakeResponse(200, json_data={"children": ["c1", "c2"]})

    done = pb.poll_batch(session_for(resp), info, conn)

    assert done is False
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"


def test_complete_children_mark_parent_complete(monkeypatch, conn):
    info = batch_info()
    monkeypatch.setattr(pb, "handle_children", lambda *a: (2, 0, True))
    resp = FakeResponse(200, json_data={"children": ["c1", "c2"]})

    done = pb.poll_batch(session_for(resp), info, conn)

    assert done is True
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "COMPLETE"


def test_error_parent_with_children_is_processed_not_written_off(monkeypatch, conn):
    """An ERROR parent that still lists children is not terminal.

    The platform labels a multi-sim parent ERROR while listing the children
    that hold the results; writing the batch off on the label alone discards
    simulations the budget already paid for.
    """
    info = batch_info(submitted_at=time.time() - 600)  # well past MIN_ERROR_AGE_SEC
    info["error_strikes"] = 5  # every write-off precondition already met
    called = []
    monkeypatch.setattr(pb, "handle_children", lambda *a: (called.append(1), (2, 0, True))[1])
    resp = FakeResponse(200, json_data={"status": "ERROR", "children": ["c1", "c2"]})

    assert pb.poll_batch(session_for(resp), info, conn) is True

    assert called, "children were never fetched"
    row = conn.execute("SELECT status, error_message FROM simulations WHERE sim_id='P1'").fetchone()
    assert row == ("COMPLETE", None)
