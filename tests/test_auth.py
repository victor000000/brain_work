"""Fix 7: AuthError instead of sys.exit, credential validation, failure mode.

No network: session creation is exercised with _load_credentials /
_authenticate stubbed, and credential parsing points PROJECT_DIR at tmp_path.
"""

import json

import pytest

import core.auth as auth


class FakeAuthSession:
    def __init__(self):
        self.auth = None
        self.post_calls = 0

    def post(self, url, **kwargs):
        self.post_calls += 1
        raise ConnectionError("no network in tests")


def test_get_session_raise_on_failure_raises_autherror(monkeypatch):
    monkeypatch.setattr(auth, "_load_credentials", lambda s: False)
    with pytest.raises(auth.AuthError):
        auth.get_session(raise_on_failure=True)


def test_get_session_default_still_exits(monkeypatch):
    monkeypatch.setattr(auth, "_load_credentials", lambda s: False)
    with pytest.raises(SystemExit):
        auth.get_session()


def test_get_session_raise_on_failure_when_auth_rejected(monkeypatch):
    monkeypatch.setattr(auth, "_load_credentials", lambda s: True)
    monkeypatch.setattr(auth, "_authenticate", lambda s: False)
    with pytest.raises(auth.AuthError):
        auth.get_session(raise_on_failure=True)


def _point_credentials_at(monkeypatch, tmp_path, content):
    cred_file = tmp_path / ".brain_credentials"
    cred_file.write_text(content)
    monkeypatch.setattr(auth, "PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))


def test_valid_credentials_file_loaded(monkeypatch, tmp_path):
    _point_credentials_at(monkeypatch, tmp_path, json.dumps(["user@example.com", "secret"]))
    session = FakeAuthSession()
    assert auth._load_credentials(session) is True
    assert session.auth == ("user@example.com", "secret")


@pytest.mark.parametrize(
    "content",
    [
        json.dumps({"email": "a@b.c", "password": "pw"}),  # object, not list
        json.dumps(["only-one"]),
        json.dumps(["a", "b", "c"]),
        json.dumps([1, 2]),  # non-strings
        "{not json",
        json.dumps("user@example.com"),
    ],
)
def test_malformed_credentials_rejected(monkeypatch, tmp_path, content):
    _point_credentials_at(monkeypatch, tmp_path, content)
    session = FakeAuthSession()
    assert auth._load_credentials(session) is False
    assert session.auth is None


def test_authenticate_does_not_raise_on_transport_error(monkeypatch):
    """Exhausted transport retries return False — they never raise.

    `post_calls` was pinned at 1 when a failure was final; it is now the
    retry budget, because a transport error is transient and cost a full
    explorer exit each time — nine of them on 2026-10-08 against five rate
    limits. The behaviour this test exists for (no exception escapes) is
    unchanged, and a *non-2xx* is still final on the first response.
    """
    from core import auth_http

    monkeypatch.setattr(auth_http.time, "sleep", lambda _s: None)
    session = FakeAuthSession()
    assert auth._authenticate(session) is False
    assert session.post_calls == auth_http.AUTH_TRANSPORT_RETRIES + 1


def test_a_transport_error_is_retried_before_giving_up(monkeypatch):
    """One flaky POST must not cost the whole start-up."""
    from core import auth_http

    monkeypatch.setattr(auth_http.time, "sleep", lambda _s: None)
    session = _ScriptedSession(
        [
            ConnectionError("read timed out"),
            _FakeResponse(201, payload={"user": {"id": "u1"}}),
        ]
    )

    assert auth._authenticate(session) is True
    assert session.post_calls == 2


def test_a_rejected_credential_is_not_retried(monkeypatch):
    """Only a *transport* failure is transient; a 401 is the platform answering."""
    clock = _frozen_clock(monkeypatch)
    session = _ScriptedSession([_FakeResponse(401, text="invalid credentials")])

    assert auth._authenticate(session) is False
    assert session.post_calls == 1, "a real rejection must fail fast"
    assert clock.slept == []


class _FakeResponse:
    def __init__(self, status_code, headers=None, text="", payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text
        self._payload = payload or {}

    def json(self):
        return self._payload


class _ScriptedSession:
    """Returns each queued response in turn; counts the POSTs.

    A queued item that is an exception is raised, so a transport failure can be
    scripted alongside responses.
    """

    def __init__(self, responses):
        self._responses = list(responses)
        self.post_calls = 0

    def post(self, url, **kwargs):
        self.post_calls += 1
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _Clock:
    """Stands in for `core.auth_http.time`, recording what was slept."""

    def __init__(self):
        self.slept = []

    def sleep(self, seconds):
        self.slept.append(seconds)


def _frozen_clock(monkeypatch):
    from core import auth_http

    clock = _Clock()
    # Patch the module attribute, not `time.sleep` on the shared module, which
    # would stop the clock for every other test running alongside this one.
    monkeypatch.setattr(auth_http, "time", clock)
    return clock


def test_a_rate_limited_auth_is_waited_out_not_reported_as_bad_credentials(monkeypatch):
    """A spent auth window is transient, and `get_session` calls it fatal.

    The endpoint allows 5 POSTs a minute and names the wait in `Retry-After`
    (measured 2026-10-08). Reporting the 429 as a failure made the explorer
    exit with "no valid credentials or auth rejected" — a wrong diagnosis that
    the supervisor then repeated every 15s, holding the window spent.
    """
    clock = _frozen_clock(monkeypatch)
    session = _ScriptedSession(
        [
            _FakeResponse(429, {"Retry-After": "38"}, text="rate limit"),
            _FakeResponse(201, payload={"user": {"id": "u1"}}),
        ]
    )

    assert auth._authenticate(session) is True
    assert session.post_calls == 2
    assert clock.slept == [38.0], "the endpoint's own Retry-After is the wait"


def test_a_rate_limit_without_retry_after_is_not_retried(monkeypatch):
    """No `Retry-After` means no stated window to wait for, so don't spin."""
    clock = _frozen_clock(monkeypatch)
    session = _ScriptedSession([_FakeResponse(429, {}, text="rate limit")])

    assert auth._authenticate(session) is False
    assert session.post_calls == 1
    assert clock.slept == []


def test_a_retry_after_beyond_the_cap_is_not_slept_through(monkeypatch):
    """A long window is the supervisor's to ride out, not a blocking sleep."""
    from core import auth_http

    clock = _frozen_clock(monkeypatch)
    session = _ScriptedSession([_FakeResponse(429, {"Retry-After": "3600"}, text="rate limit")])

    assert auth._authenticate(session) is False
    assert session.post_calls == 1
    assert clock.slept == []
    assert auth_http.AUTH_RETRY_CAP_SEC < 3600


def test_a_persistent_rate_limit_gives_up_after_its_retries(monkeypatch):
    """The retry is bounded: a limit that will not clear is the supervisor's."""
    from core import auth_http

    clock = _frozen_clock(monkeypatch)
    session = _ScriptedSession([_FakeResponse(429, {"Retry-After": "38"}, text="rate limit")] * 10)

    assert auth._authenticate(session) is False
    assert session.post_calls == auth_http.AUTH_RATE_LIMIT_RETRIES + 1
    assert len(clock.slept) == auth_http.AUTH_RATE_LIMIT_RETRIES
