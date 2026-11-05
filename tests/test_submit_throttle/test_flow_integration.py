"""check_and_submit holds alphas during cooldown and returns HELD."""

from unittest.mock import MagicMock

import pytest

from core.db import connect
from core.db.schema_sql import SCHEMA_SQL


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript(SCHEMA_SQL)
    c.execute("ALTER TABLE alpha_results ADD COLUMN template TEXT")
    c.execute(
        "INSERT INTO alpha_results "
        "(alpha_id, template, region, universe, delay, neutralization, status) "
        "VALUES ('A1', 'T', 'CHN', 'TOP2000U', 0, 'NONE', 'UNSUBMITTED')"
    )
    c.commit()
    yield c
    c.close()


def test_throttled_alpha_recorded_in_throttle_state(monkeypatch, conn):
    from runner.submit import flow

    flow._reset_throttle_state()
    monkeypatch.setattr(flow, "ensure_description", lambda *a, **k: None)
    monkeypatch.setattr(flow, "try_submit", lambda *a, **k: (429, None))
    monkeypatch.setattr(flow, "verify_submission", lambda *a, **k: "SUBMITTED")
    monkeypatch.setattr(flow, "fallback_get_check", lambda *a, **k: "FAIL:other")
    monkeypatch.setattr(flow, "update_alpha_status", lambda *a, **k: None)

    result = flow.check_and_submit(MagicMock(), conn, "A1")
    assert result == "THROTTLED"
    assert len(flow._throttle_events[("CHN", "TOP2000U", 0)]) == 1


def test_held_alpha_queued_when_cooldown_active(monkeypatch, conn):
    from runner.submit import flow

    flow._reset_throttle_state()
    cell = ("CHN", "TOP2000U", 0)
    now = 100.0
    for i in range(flow.THROTTLE_THRESHOLD):
        flow.record_throttle(cell, now=now + i * 0.1)

    monkeypatch.setattr(flow, "ensure_description", lambda *a, **k: None)
    monkeypatch.setattr(
        flow,
        "try_submit",
        lambda *a, **k: pytest.fail("try_submit should not be called during cooldown"),
    )
    monkeypatch.setattr(flow, "update_alpha_status", lambda *a, **k: None)
    monkeypatch.setattr(flow.time, "time", lambda: now + 1.0)

    result = flow.check_and_submit(MagicMock(), conn, "A1")
    assert result == "HELD"
    assert flow.drain_held_alpha(cell) == "A1"
