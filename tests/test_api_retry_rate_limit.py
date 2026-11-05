"""Retry policy for POST /simulations: 429 waits and budget exhaustion."""

import core.api_retry as api_retry
import core.budget as budget
from tests import test_api_retry_helpers as helpers
from tests.test_api_retry_helpers import FakeResponse, FakeSession, clean_budget  # noqa: F401

# Bound here rather than imported by name: a direct import of `sleeps` would be
# shadowed by the test parameters of the same name (ruff F811).
sleeps = helpers.sleeps


def test_429_uses_retry_after_header(sleeps):
    session = FakeSession([FakeResponse(429, {"Retry-After": "2"}, text="rate limited"), FakeResponse(201)])
    assert api_retry.post_simulation(session, {}, 1).status_code == 201
    assert sleeps == [api_retry.RATE_LIMIT_WAIT]  # floor still applies


def test_429_uses_x_ratelimit_reset_when_no_retry_after(sleeps):
    session = FakeSession(
        [
            FakeResponse(429, {"X-Ratelimit-Remaining": "900", "X-Ratelimit-Reset": "12"}, text="rate limited"),
            FakeResponse(201),
        ]
    )
    api_retry.post_simulation(session, {}, 1)
    assert sleeps == [12]


def test_429_ignores_wrongly_named_reset_header(sleeps):
    """The platform header is X-Ratelimit-Reset; RateLimit-Reset must not drive the wait."""
    session = FakeSession([FakeResponse(429, {"RateLimit-Reset": "500"}, text="rate limited"), FakeResponse(201)])
    api_retry.post_simulation(session, {}, 1)
    assert sleeps == [api_retry.RATE_LIMIT_WAIT]


def test_malformed_reset_header_never_raises(sleeps):
    session = FakeSession([FakeResponse(429, {"X-Ratelimit-Reset": "soon"}, text="rate limited"), FakeResponse(201)])
    assert api_retry.post_simulation(session, {}, 1).status_code == 201
    assert sleeps == [api_retry.RATE_LIMIT_WAIT]


def test_large_reset_marks_budget_exhausted(sleeps):
    session = FakeSession([FakeResponse(429, {"X-Ratelimit-Reset": "900"}, text="rate limited")])
    assert api_retry.post_simulation(session, {}, 1) == "BUDGET"
    assert budget.is_exhausted() is True
    assert sleeps == []


def test_concurrent_429_returns_concurrent(sleeps):
    session = FakeSession([FakeResponse(429, {}, text="CONCURRENT_LIMIT reached")])
    assert api_retry.post_simulation(session, {}, 1) == "CONCURRENT"
    sess = session
    assert len(sess.calls) == 1


def test_known_exhausted_budget_short_circuits(sleeps):
    budget.mark_exhausted(600)
    session = FakeSession([FakeResponse(201)])
    assert api_retry.post_simulation(session, {}, 1) == "BUDGET"
    assert session.calls == []
