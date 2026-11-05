"""Fix 2: TimeoutSession injects a default HTTP timeout and honors env overrides."""

import pytest
import requests

import core.auth as auth


def test_default_timeout_is_injected(monkeypatch):
    seen = {}

    def fake_request(self, method, url, **kwargs):
        seen.update(kwargs)
        return "response"

    monkeypatch.setattr(requests.Session, "request", fake_request)
    session = auth.TimeoutSession()
    assert session.get("https://example.invalid/x") == "response"
    assert seen["timeout"] == auth.DEFAULT_HTTP_TIMEOUT


def test_explicit_timeout_is_kept(monkeypatch):
    seen = {}

    def fake_request(self, method, url, **kwargs):
        seen.update(kwargs)
        return "response"

    monkeypatch.setattr(requests.Session, "request", fake_request)
    session = auth.TimeoutSession()
    session.post("https://example.invalid/x", timeout=1.5)
    assert seen["timeout"] == 1.5


def test_env_override_connect_read(monkeypatch):
    monkeypatch.setenv(auth.TIMEOUT_ENV_VAR, "1.5, 20")
    assert auth.TimeoutSession().default_timeout == (1.5, 20.0)


def test_env_override_single_value_applies_to_both(monkeypatch):
    monkeypatch.setenv(auth.TIMEOUT_ENV_VAR, "7")
    assert auth.TimeoutSession().default_timeout == (7.0, 7.0)


@pytest.mark.parametrize(
    "bad",
    ["", "abc", "1,2,3", "1,x", "-", "0", "-1", "nan", "inf", "-inf", "5,0", "0,5", "nan,30", "5,inf", "5,-1"],
)
def test_bad_env_falls_back_to_default(monkeypatch, bad):
    monkeypatch.setenv(auth.TIMEOUT_ENV_VAR, bad)
    assert auth.TimeoutSession().default_timeout == auth.DEFAULT_HTTP_TIMEOUT


def test_get_session_returns_timeout_session(monkeypatch):
    monkeypatch.setattr(auth, "_load_credentials", lambda s: True)
    monkeypatch.setattr(auth, "_authenticate", lambda s: True)
    session = auth.get_session()
    assert isinstance(session, auth.TimeoutSession)
    assert session.default_timeout == auth.DEFAULT_HTTP_TIMEOUT
