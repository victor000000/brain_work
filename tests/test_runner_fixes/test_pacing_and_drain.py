"""FIX 12: in-flight polling honours the minimum interval and the Retry-After
backoff, and a batch that raises is kept for a later retry."""

import time
from unittest.mock import MagicMock

import pytest

from runner.explore_loop import poll as pollmod
from tests.test_runner_fixes.helpers import batch_info


def test_poll_inflight_respects_min_interval(monkeypatch):
    state = {"inflight": [batch_info()], "last_poll_ts": time.time(), "poll_backoff_until": 0.0}
    monkeypatch.setattr(pollmod, "poll_batch", lambda *a: pytest.fail("polled inside min interval"))

    assert pollmod.poll_inflight(MagicMock(), state, None) == 0


def test_poll_inflight_respects_retry_after_backoff(monkeypatch):
    state = {
        "inflight": [batch_info()],
        "last_poll_ts": time.time() - 10 * pollmod.MIN_POLL_INTERVAL_SEC,
        "poll_backoff_until": time.time() + 60,
    }
    monkeypatch.setattr(pollmod, "poll_batch", lambda *a: pytest.fail("polled while backing off"))

    assert pollmod.poll_inflight(MagicMock(), state, None) == 0


def test_poll_inflight_sets_backoff_from_retry_after(monkeypatch):
    def fake_poll(session, batch, conn):
        batch["retry_after"] = 30
        return False

    batch = batch_info()
    state = {"inflight": [batch], "last_poll_ts": 0.0, "poll_backoff_until": 0.0}
    monkeypatch.setattr(pollmod, "poll_batch", fake_poll)

    assert pollmod.poll_inflight(MagicMock(), state, None) == 0
    assert state["poll_backoff_until"] > time.time() + 25


def test_poll_inflight_survives_a_batch_exception(monkeypatch):
    def boom(session, batch, conn):
        raise RuntimeError("kaboom")

    batch = batch_info()
    state = {"inflight": [batch], "last_poll_ts": 0.0, "poll_backoff_until": 0.0}
    monkeypatch.setattr(pollmod, "poll_batch", boom)

    assert pollmod.poll_inflight(MagicMock(), state, None) == 0
    assert state["inflight"] == [batch]  # kept for a later retry, not dropped
