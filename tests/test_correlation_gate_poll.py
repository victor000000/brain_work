"""Retry-After polling for the correlation endpoints."""

from tests.test_correlation_gate_helpers import FakeResponse, FakeSession


def test_polling_does_not_hammer_a_one_second_retry_after(monkeypatch):
    """`Retry-After: 1` is a "still queued" hint, not a one-second promise.

    Honouring it literally spent a 60s deadline issuing ~60 requests against an
    already-congested endpoint and still returned an empty body.
    """
    from core import api_poll

    slept = []
    monkeypatch.setattr(api_poll.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(api_poll.time, "time", lambda: 0.0)  # the deadline never arrives

    calls = []

    def counting(url, timeout=None):
        calls.append(1)
        if len(calls) >= 4:
            return FakeResponse(200, {"max": 0.1})
        return FakeResponse(200, {"message": "computing"}, headers={"Retry-After": "1"})

    session = FakeSession([])
    session.get = counting

    resp = api_poll._poll_until_ready(session, "/x", timeout=1e9)

    assert resp.json() == {"max": 0.1}
    assert len(calls) == 4
    assert slept and all(s >= api_poll.MIN_POLL_SLEEP_SEC for s in slept), slept


def test_non_finite_retry_after_is_treated_as_absent():
    """A mangled Retry-After must not reach time.sleep() and kill the poll."""
    import core.api as api

    for raw in ("nan", "inf", "-inf"):
        resp = FakeResponse(503, json_data={"progress": 0.1}, headers={"Retry-After": raw})
        assert api._retry_after_seconds(resp) is None
