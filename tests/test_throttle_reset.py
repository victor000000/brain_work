"""Retry-After / RateLimit-Reset handling on responses."""

from tests.test_throttle_helpers import Host, Resp, _handle

# ── Retry-After / RateLimit-Reset parsing ─────────────────────────
#
# A missing, empty, or RFC-7231-date header used to raise ValueError inside
# _handle, killing the refresh. Retry-After was also honored on any status, so
# a 200 carrying one was silently re-issued.


def test_empty_ratelimit_reset_on_429_does_not_crash(monkeypatch):
    h = Host()
    out, sleeps = _handle(h, Resp({"RateLimit-Reset": ""}, status_code=429), monkeypatch)
    assert out is None
    assert sleeps == [2.0]


def test_garbage_ratelimit_reset_on_429_does_not_crash(monkeypatch):
    h = Host()
    out, sleeps = _handle(h, Resp({"RateLimit-Reset": "not-a-number"}, status_code=429), monkeypatch)
    assert out is None
    assert sleeps == [2.0]


def test_rfc7231_reset_date_on_429_is_parsed(monkeypatch):
    import email.utils

    h = Host()
    when = email.utils.formatdate(usegmt=True)  # now-ish -> clamps to the 2s floor
    out, sleeps = _handle(h, Resp({"RateLimit-Reset": when}, status_code=429), monkeypatch)
    assert out is None
    assert sleeps and sleeps[0] == 2.0


def test_retry_after_on_a_200_is_not_retried(monkeypatch):
    h = Host()
    resp = Resp({"Retry-After": "5"}, status_code=200)
    out, sleeps = _handle(h, resp, monkeypatch)
    assert out is resp
    assert sleeps == []


def test_retry_after_honored_on_a_retryable_status(monkeypatch):
    h = Host()
    out, sleeps = _handle(h, Resp({"Retry-After": "3"}, status_code=503), monkeypatch)
    assert out is None
    assert sleeps == [3.0]


def test_retry_after_garbage_on_503_is_ignored(monkeypatch):
    h = Host()
    resp = Resp({"Retry-After": "soon"}, status_code=503)
    out, sleeps = _handle(h, resp, monkeypatch)
    assert out is resp
    assert sleeps == []


def test_rfc7231_retry_after_on_503_is_parsed(monkeypatch):
    import email.utils

    h = Host()
    when = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
    resp = Resp({"Retry-After": when}, status_code=503)
    out, sleeps = _handle(h, resp, monkeypatch)
    # A date in the past -> 0 seconds -> treated as no retry delay
    assert out is resp
    assert sleeps == []


def test_huge_retry_after_is_capped(monkeypatch):
    from download.session_throttle import MAX_RETRY_SLEEP

    h = Host()
    out, sleeps = _handle(h, Resp({"Retry-After": "99999"}, status_code=503), monkeypatch)
    assert out is None
    assert sleeps == [MAX_RETRY_SLEEP]
