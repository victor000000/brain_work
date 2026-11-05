"""FIX 13: the held-alpha queue drains after cooldown, is bounded per pass and
requeues an alpha the platform still holds."""

import time
from unittest.mock import MagicMock

import pytest

from runner.submit import flow


def test_drain_held_queue_submits_after_cooldown(monkeypatch, conn):
    flow._reset_throttle_state()
    cell = ("USA", "TOP3000", 1)
    flow.queue_held_alpha(cell, "A1")
    called = []
    monkeypatch.setattr(flow, "check_and_submit", lambda session, c, alpha_id: called.append(alpha_id) or "SUBMITTED")

    assert flow.drain_held_queue(MagicMock(), conn) == 1
    assert called == ["A1"]
    assert cell not in flow._held_alphas  # empty queue cleaned up


def test_drain_held_queue_skips_cells_in_cooldown(monkeypatch, conn):
    flow._reset_throttle_state()
    cell = ("USA", "TOP3000", 1)
    now = time.time()
    for _ in range(flow.THROTTLE_THRESHOLD):
        flow.record_throttle(cell, now=now)
    flow.queue_held_alpha(cell, "A1")
    monkeypatch.setattr(flow, "check_and_submit", lambda *a: pytest.fail("submitted during cooldown"))

    assert flow.drain_held_queue(MagicMock(), conn, now=now) == 0
    assert list(flow._held_alphas[cell]) == ["A1"]


def test_drain_held_queue_is_bounded(monkeypatch, conn):
    flow._reset_throttle_state()
    for i in range(4):
        flow.queue_held_alpha((f"R{i}", "TOP3000", 1), f"A{i}")
    monkeypatch.setattr(flow, "check_and_submit", lambda *a: "SUBMITTED")

    assert flow.drain_held_queue(MagicMock(), conn, max_submits=3) == 3
    remaining = sum(len(q) for q in flow._held_alphas.values())
    assert remaining == 1


def test_drain_held_queue_requeues_held_alpha(monkeypatch, conn):
    flow._reset_throttle_state()
    cell = ("USA", "TOP3000", 1)
    flow.queue_held_alpha(cell, "A1")
    monkeypatch.setattr(flow, "check_and_submit", lambda *a: "HELD")

    assert flow.drain_held_queue(MagicMock(), conn) == 1
    assert list(flow._held_alphas[cell]) == ["A1"]
