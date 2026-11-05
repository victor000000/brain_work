"""Observation clocks never cancel or release accepted native jobs."""

import time
from unittest.mock import MagicMock

from runner.explore_loop import poll as pollmod
from runner.explore_loop.constants import STALE_HARD_TIMEOUT
from tests.test_runner_fixes.helpers import FakeResponse, parent_row, stale_batch


def test_drop_stale_defers_while_throttled(conn):
    batch = stale_batch()
    state = {"inflight": [batch], "poll_throttled": True}
    session = MagicMock()

    pollmod.drop_stale(session, state, conn)

    assert state["inflight"] == [batch]
    session.delete.assert_not_called()


def test_throttle_clears_without_cancelling_unresolved_parent(conn):
    """A 429 then a 404 must not keep state["poll_throttled"] set forever:
    Slow-job handling retains the unresolved parent after throttling clears."""
    parent_row(conn)
    batch = stale_batch()
    state = {"inflight": [batch], "last_poll_ts": 0.0, "poll_backoff_until": 0.0}
    session = MagicMock()
    session.get.side_effect = [
        FakeResponse(429, headers={"Retry-After": "7"}),
        FakeResponse(404),
        FakeResponse(404),
    ]
    session.delete.return_value = FakeResponse(204)

    pollmod.poll_inflight(session, state, conn)
    assert state["poll_throttled"] is True
    pollmod.drop_stale(session, state, conn)
    assert state["inflight"] == [batch]  # deferred, as designed

    state["last_poll_ts"] = 0.0
    state["poll_backoff_until"] = 0.0
    pollmod.poll_inflight(session, state, conn)
    assert state["poll_throttled"] is False
    pollmod.drop_stale(session, state, conn)
    assert state["inflight"] == [batch]
    session.delete.assert_not_called()
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"


def test_a_batch_still_reporting_progress_is_not_dropped(conn):
    """Age alone must not discard work the budget already paid for.

    HKG/TOP800 batches routinely sit near 35% past STALE_TIMEOUT and finish
    afterwards; dropping them threw those simulations away.
    """
    batch = stale_batch()
    batch["last_advance_at"] = time.time() - 30  # progress 30s ago
    batch["progress"] = 35.0
    state = {"inflight": [batch]}
    session = MagicMock()

    pollmod.drop_stale(session, state, conn)

    assert state["inflight"] == [batch]
    session.delete.assert_not_called()


def test_a_batch_past_the_hard_ceiling_is_retained_even_if_progressing(conn):
    """Age cannot authorize cancelling a still-progressing native job."""
    batch = stale_batch()
    batch["submitted_at"] = time.time() - STALE_HARD_TIMEOUT - 10
    batch["last_advance_at"] = time.time() - 5
    state = {"inflight": [batch]}
    session = MagicMock()
    session.delete.return_value = FakeResponse(204)

    pollmod.drop_stale(session, state, conn)

    assert state["inflight"] == [batch]
    session.delete.assert_not_called()


def test_stationary_progress_beyond_timeout_retains_parent_and_limits_notices(conn, monkeypatch):
    from runner.explore_loop import poll_stale

    parent_row(conn)
    batch = stale_batch()
    batch["progress"] = 35.0
    state = {"inflight": [batch]}
    session = MagicMock()
    warning = MagicMock()
    monkeypatch.setattr(poll_stale.elog, "warning", warning)
    pollmod.drop_stale(session, state, conn)
    pollmod.drop_stale(session, state, conn)
    assert state["inflight"] == [batch]
    session.delete.assert_not_called()
    session.post.assert_not_called()
    warning.assert_called_once()
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone()[0] == "SUBMITTED"
