"""Hostile header values must not crash the throttle or poison its state."""

from tests.test_throttle_helpers import Host, Resp, _handle


def test_garbage_headers_do_not_crash():
    h = Host()
    h._adapt(Resp({"X-RateLimit-Remaining-Minute": "abc", "X-RateLimit-Limit-Minute": "??"}))
    h._adapt(
        Resp(
            {"X-RateLimit-Remaining-Minute": "10", "X-RateLimit-Limit-Minute": "x", "X-RateLimit-Remaining-Second": "y"}
        )
    )
    assert h._interval > 0


def test_adapt_survives_hostile_reset_and_throttle_does_not_raise(monkeypatch):
    """End-to-end: the hostile header must not poison `_interval`."""
    import time as _time
    import types

    h = Host()
    h._adapt(
        Resp(
            {
                "X-RateLimit-Remaining-Minute": "0",
                "X-RateLimit-Limit-Minute": "30",
                "RateLimit-Reset": "1e400",
            }
        )
    )
    assert h._interval != float("inf") and h._interval <= 5.0  # unparseable -> 5s default

    sleeps = []
    monkeypatch.setattr("download.session_throttle.time", types.SimpleNamespace(time=_time.time, sleep=sleeps.append))
    h._last_req = _time.time()
    h._throttle()
    assert sleeps and sleeps[0] <= 5.0


def test_handle_429_with_hostile_reset_does_not_crash(monkeypatch):
    h = Host()
    out, sleeps = _handle(h, Resp({"RateLimit-Reset": "1e400"}, status_code=429), monkeypatch)
    assert out is None
    assert sleeps == [2.0]
