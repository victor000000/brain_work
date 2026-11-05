"""Fakes and fixtures shared by the probe lifecycle tests."""

import pytest

from tools.probe_simulation_combos import probe as probe_mod


class Resp:
    def __init__(self, status_code, headers=None, text="", body=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text
        self._body = body if body is not None else {}

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.cancelled = []

    def post(self, url, json=None, timeout=None):
        return self.responses.pop(0)

    def delete(self, url, timeout=None):
        self.cancelled.append(url)
        return Resp(200)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(probe_mod.time, "sleep", lambda _s: None)
