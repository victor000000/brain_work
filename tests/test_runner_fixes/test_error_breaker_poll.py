"""The poll pass itself feeds the simulation-error breaker."""

import time
from unittest.mock import MagicMock

from runner.explore_loop import poll as pollmod
from tests.test_runner_fixes.helpers import batch_info


def test_poll_inflight_feeds_the_breaker(monkeypatch):
    """A batch that completes with no results counts as a failure."""
    state = {
        "inflight": [batch_info(), batch_info(pid="P2")],
        "done_count": 0,
        "last_poll_ts": 0.0,
        "poll_backoff_until": 0.0,
    }

    def fake_poll(session, batch, conn):
        batch["failed"] = True
        return True

    monkeypatch.setattr(pollmod, "poll_batch", fake_poll)
    assert pollmod.poll_inflight(MagicMock(), state, None) == 2
    assert state["sim_error_streak"] == 2


def test_poll_inflight_arms_the_pause_on_the_fourth_failure(monkeypatch):
    """The pause is armed by the poll pass itself — no gate evaluation needed."""
    state = {
        "inflight": [batch_info() for _ in range(4)],
        "done_count": 0,
        "last_poll_ts": 0.0,
        "poll_backoff_until": 0.0,
        "sim_error_streak": 3,  # three earlier failures
    }

    def fake_poll(session, batch, conn):
        batch["failed"] = True
        return True

    monkeypatch.setattr(pollmod, "poll_batch", fake_poll)
    assert pollmod.poll_inflight(MagicMock(), state, None) == 4
    assert state["sim_error_pause_until"] > time.time()


def test_poll_inflight_resets_streak_on_a_clean_completion(monkeypatch):
    state = {
        "inflight": [batch_info()],
        "done_count": 0,
        "last_poll_ts": 0.0,
        "poll_backoff_until": 0.0,
        "sim_error_streak": 3,
    }
    monkeypatch.setattr(pollmod, "poll_batch", lambda *a: True)
    assert pollmod.poll_inflight(MagicMock(), state, None) == 1
    assert state["sim_error_streak"] == 0
