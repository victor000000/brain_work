"""FIX 6 (checker half): bounded, Retry-After-aware check calls that never
hang or raise on malformed headers."""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import MagicMock

from checker import check_via_get as cg
from checker import check_via_submit as cs
from tests.test_runner_fixes.helpers import FakeResponse


def _session(resp):
    session = MagicMock()
    session.post.return_value = resp
    session.get.return_value = resp
    return session


def test_submit_check_201_and_403(monkeypatch):
    monkeypatch.setattr(cs.time, "sleep", lambda *_: None)
    assert cs.check_via_submit(_session(FakeResponse(201)), "A1") == (201, [])

    body = {"is": {"checks": [{"name": "LOW_SHARPE", "result": "FAIL"}]}}
    assert cs.check_via_submit(_session(FakeResponse(403, json_data=body)), "A1") == (403, body["is"]["checks"])

    assert cs.check_via_submit(_session(FakeResponse(403, text="")), "A1") == (403, None)


def test_submit_check_429_gives_up_bounded_and_reports_throttle(monkeypatch):
    monkeypatch.setattr(cs.time, "sleep", lambda *_: None)
    resp = FakeResponse(429, headers={"Retry-After": "0"})

    assert cs.check_via_submit(_session(resp), "A1") == (429, None)


def test_submit_check_retry_after_date_does_not_raise(monkeypatch):
    monkeypatch.setattr(cs.time, "sleep", lambda *_: None)
    when = datetime.now(UTC) + timedelta(seconds=1)
    resp = FakeResponse(429, headers={"Retry-After": format_datetime(when)})

    code, checks = cs.check_via_submit(_session(resp), "A1")

    assert code == 429
    assert checks is None


def test_submit_check_deadline_is_checked_before_requests(monkeypatch):
    monkeypatch.setattr(cs, "TOTAL_DEADLINE_SEC", -1)
    session = _session(FakeResponse(201))

    assert cs.check_via_submit(session, "A1") == (None, None)
    session.post.assert_not_called()


def test_get_check_returns_checks(monkeypatch):
    monkeypatch.setattr(cg.time, "sleep", lambda *_: None)
    body = {"is": {"checks": [{"name": "LOW_SHARPE", "result": "PASS"}]}}

    assert cg.check_via_get(_session(FakeResponse(200, json_data=body)), "A1") == body["is"]["checks"]


def test_get_check_persistent_429_is_bounded(monkeypatch):
    monkeypatch.setattr(cg, "MAX_POLL_SECONDS", 0.05)
    monkeypatch.setattr(cg, "DEFAULT_429_WAIT", 100)
    monkeypatch.setattr(cg.time, "sleep", lambda *_: None)
    resp = FakeResponse(429, headers={"Retry-After": "100"})

    assert cg.check_via_get(_session(resp), "A1") is None


def _fake_clock(monkeypatch):
    """A monotonic clock that only advances when the code under test sleeps."""
    slept = []
    clock = {"t": 0.0}

    def sleep(seconds):
        slept.append(seconds)
        clock["t"] += seconds

    monkeypatch.setattr(cg.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(cg.time, "sleep", sleep)
    return slept


def test_get_check_empty_body_follows_retry_after(monkeypatch):
    """An empty-body 200 is paced by the platform's Retry-After, not by 8s.

    Regression for the empty-preview stall: at a flat 8s a 5s window affords a
    single look at a computation that can take 31s to appear, and every one of
    those checks was paid for and thrown away.
    """
    monkeypatch.setattr(cg, "MAX_POLL_SECONDS", 5)
    slept = _fake_clock(monkeypatch)
    resp = FakeResponse(200, headers={"Retry-After": "1.0"})  # 200, empty body

    assert cg.check_via_get(_session(resp), "A1") is None
    assert slept == [1.0] * 5


def test_get_check_empty_body_without_retry_after_uses_default(monkeypatch):
    monkeypatch.setattr(cg, "MAX_POLL_SECONDS", 16)
    slept = _fake_clock(monkeypatch)
    resp = FakeResponse(200)  # 200, empty body, no Retry-After

    assert cg.check_via_get(_session(resp), "A1") is None
    assert slept == [cg.EMPTY_BODY_WAIT_SEC] * 2


def test_get_check_retry_after_date_does_not_raise(monkeypatch):
    monkeypatch.setattr(cg.time, "sleep", lambda *_: None)
    when = datetime.now(UTC) + timedelta(seconds=1)
    body = {"is": {"checks": []}}

    assert (
        cg.check_via_get(
            _session(FakeResponse(200, json_data=body, headers={"Retry-After": format_datetime(when)})), "A1"
        )
        == []
    )
