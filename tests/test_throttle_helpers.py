"""Doubles and the response-handling harness shared by the throttle tests."""

from download.session_throttle import MIN_INTERVAL, ThrottleMixin


class Host(ThrottleMixin):
    def __init__(self):
        self._last_req = 0.0
        self._interval = MIN_INTERVAL


class Resp:
    def __init__(self, headers=None, status_code=200):
        self.headers = headers or {}
        self.status_code = status_code


def _handle(h, resp, monkeypatch):
    sleeps = []
    monkeypatch.setattr("download.session_throttle.time.sleep", sleeps.append)
    out = h._handle(resp, "https://example.test/x")
    return out, sleeps
