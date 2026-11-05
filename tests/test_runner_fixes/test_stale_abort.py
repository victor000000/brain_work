"""Only native acknowledgement or reconciled results release accepted jobs."""

from unittest.mock import MagicMock

import pytest

from runner.explore_loop import poll as pollmod
from tests.test_runner_fixes.helpers import FakeResponse, parent_row, stale_batch


def explicit_cancel(session, state, conn):
    """Exercise explicit cancellation, separate from automatic slow-job handling."""
    state["inflight"] = [batch for batch in state["inflight"] if not pollmod._abort_server_side(session, batch, conn)]


def test_explicit_cancel_aborts_server_side_and_marks_cancelled(conn):
    parent_row(conn)
    batch = stale_batch()
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.return_value = FakeResponse(204)

    explicit_cancel(session, state, conn)

    assert state["inflight"] == []
    session.delete.assert_called_once_with(batch["loc"], timeout=20)
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "CANCELLED"


def test_refused_delete_because_complete_fetches_instead_of_dropping(conn, monkeypatch):
    """BRAIN will not delete a finished simulation — so fetch it.

    The batch stopped reporting progress, but the budget was spent and the
    result is sitting there. Dropping it threw the alphas away; observed six
    times by 2026-10-06.
    """
    parent_row(conn)
    batch = stale_batch()
    batch["error_strikes"] = 5
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.return_value = FakeResponse(400, json_data=["Can not delete complete simulations"])

    fetched = []
    monkeypatch.setattr(pollmod, "poll_batch", lambda *a: (fetched.append(1), True)[1])

    explicit_cancel(session, state, conn)

    assert fetched, "the finished batch was never fetched"
    assert state["inflight"] == []
    # Fetched, not written off: the cancel path must not have run.
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"


def test_unreadable_finished_batch_is_kept_with_backoff_then_reconciled(conn, monkeypatch):
    """A final-fetch deadline must not discard accepted results."""
    parent_row(conn)
    batch = stale_batch()
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.return_value = FakeResponse(400, json_data=["Can not delete complete simulations"])
    monkeypatch.setattr(pollmod, "poll_batch", lambda *a: False)

    for _ in range(pollmod.MAX_FINAL_FETCHES):
        state["inflight"] = [batch]
        explicit_cancel(session, state, conn)
        assert state["inflight"] == [batch], "gave up before its retry budget"

    state["inflight"] = [batch]
    explicit_cancel(session, state, conn)
    assert state["inflight"] == [batch]
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"
    session.delete.assert_called_once()
    batch["abort_retry_at"] = 0
    monkeypatch.setattr(pollmod, "poll_batch", lambda *a: True)
    explicit_cancel(session, state, conn)
    assert state["inflight"] == []
    session.delete.assert_called_once()


@pytest.mark.parametrize("code", [202, 404, 405, 429, 500])
def test_unconfirmed_cancellation_retains_parent_and_backs_off(conn, code):
    parent_row(conn)
    batch = stale_batch()
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.return_value = FakeResponse(code)
    explicit_cancel(session, state, conn)
    explicit_cancel(session, state, conn)
    assert state["inflight"] == [batch]
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"
    session.delete.assert_called_once()


def test_cancellation_transport_timeout_retains_parent(conn):
    parent_row(conn)
    batch = stale_batch()
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.side_effect = TimeoutError("observation timed out")
    explicit_cancel(session, state, conn)
    assert state["inflight"] == [batch]
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"


def test_cancellation_retry_after_is_honored(conn, monkeypatch):
    import time

    from runner.explore_loop import poll_abort

    parent_row(conn)
    batch = stale_batch()
    now = time.time()
    monkeypatch.setattr(poll_abort.time, "time", lambda: now)
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.return_value = FakeResponse(429, headers={"Retry-After": "600"})
    explicit_cancel(session, state, conn)
    assert batch["abort_retry_at"] == now + 600
    monkeypatch.setattr(poll_abort.time, "time", lambda: now + 61)
    explicit_cancel(session, state, conn)
    session.delete.assert_called_once()


def test_acknowledged_cancel_retries_local_persistence_without_another_delete(conn, monkeypatch):
    from runner.explore_loop import poll_abort

    parent_row(conn)
    batch = stale_batch()
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.return_value = FakeResponse(204)
    persist = poll_abort.update_sim_status
    monkeypatch.setattr(poll_abort, "update_sim_status", MagicMock(side_effect=RuntimeError("write failed")))
    explicit_cancel(session, state, conn)
    assert state["inflight"] == [batch]
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"
    monkeypatch.setattr(poll_abort, "update_sim_status", persist)
    batch["abort_retry_at"] = 0
    explicit_cancel(session, state, conn)
    assert state["inflight"] == []
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "CANCELLED"
    session.delete.assert_called_once()
