"""Retry policy for POST /simulations: Retry-After and reset-header parsing."""

import time
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

import core.api_retry as api_retry
import core.budget as budget
from tests import test_api_retry_helpers as helpers
from tests.test_api_retry_helpers import FakeResponse, FakeSession, clean_budget  # noqa: F401

# Bound here rather than imported by name: a direct import of `sleeps` would be
# shadowed by the test parameters of the same name (ruff F811).
sleeps = helpers.sleeps


def test_retry_after_accepts_http_date():
    when = datetime.now(UTC) + timedelta(seconds=30)
    resp = FakeResponse(503, {"Retry-After": format_datetime(when, usegmt=True)})
    seconds = api_retry._retry_after_seconds(resp)
    assert 25 <= seconds <= 31


def test_retry_after_past_http_date_is_zero():
    when = datetime.now(UTC) - timedelta(seconds=60)
    resp = FakeResponse(503, {"Retry-After": format_datetime(when, usegmt=True)})
    assert api_retry._retry_after_seconds(resp) == 0.0


@pytest.mark.parametrize("raw", [None, "", "later", "  ", "12.5.3"])
def test_retry_after_unparseable_returns_none(raw):
    headers = {} if raw is None else {"Retry-After": raw}
    assert api_retry._retry_after_seconds(FakeResponse(503, headers)) is None


def test_reset_seconds_falls_back_through_headers():
    resp = FakeResponse(429, {"Retry-After": "bad", "X-Ratelimit-Reset": "also-bad"})
    assert api_retry._reset_seconds(resp) == float(api_retry.RATE_LIMIT_WAIT)


def test_gateway_retry_hint_cannot_authorize_repeating_a_post(sleeps):
    session = FakeSession([FakeResponse(500, {"Retry-After": "99999"}), FakeResponse(201)])
    api_retry.post_simulation(session, {}, 1)
    assert len(session.calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("raw", ["inf", "-inf", "nan", "Infinity", "NaN"])
def test_non_finite_retry_after_is_treated_as_absent(raw):
    """inf/nan parse as floats but must never reach time.sleep()."""
    resp = FakeResponse(503, {"Retry-After": raw})
    assert api_retry._retry_after_seconds(resp) is None
    assert api_retry._reset_seconds(resp) == float(api_retry.RATE_LIMIT_WAIT)


def test_ambiguous_gateway_response_is_held_even_with_invalid_retry_hint(sleeps):
    session = FakeSession([FakeResponse(503, {"Retry-After": "nan"}), FakeResponse(201)])
    assert api_retry.post_simulation(session, {}, 1) is None
    assert len(session.calls) == 1
    assert sleeps == []


def test_absurd_reset_window_marks_a_bounded_exhaustion(sleeps):
    session = FakeSession([FakeResponse(429, {"X-Ratelimit-Reset": "1e300"}, text="rate limited")])
    assert api_retry.post_simulation(session, {}, 1) == "BUDGET"
    assert budget.is_exhausted() is True
    assert budget.seconds_until_reset() <= 24 * 3600 + 1


def test_retry_helpers_do_not_sleep_or_raise_on_weird_types():
    resp = FakeResponse(503, {"Retry-After": 5, "X-Ratelimit-Reset": 7})
    assert api_retry._retry_after_seconds(resp) == 5.0
    assert api_retry._reset_seconds(resp) == 5.0


def test_elapsed_wall_clock_is_bounded():
    """Sanity: retries must not sleep for absurd unpatched durations."""
    started = time.time()
    session = FakeSession([FakeResponse(500), FakeResponse(201)])
    api_retry.post_simulation(session, {}, 1)
    assert time.time() - started < 5
