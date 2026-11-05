"""Ambiguous simulation POST outcomes must never be automatically repeated."""

import pytest
from requests.exceptions import ReadTimeout

import core.api_retry as api_retry
from tests import test_api_retry_helpers as helpers
from tests.test_api_retry_helpers import FakeResponse, FakeSession, clean_budget  # noqa: F401

sleeps = helpers.sleeps


@pytest.mark.parametrize(
    "failure",
    [
        ConnectionError("response lost"),
        ReadTimeout("read timed out"),
        FakeResponse(500),
        FakeResponse(502, {"Retry-After": "3"}),
        FakeResponse(503, {"Retry-After": "99999"}),
    ],
)
def test_ambiguous_post_stops_without_a_second_request_or_claim_refund(sleeps, failure):
    session = FakeSession([failure, FakeResponse(201)])
    refunded = []
    result = api_retry.post_simulation(
        session, {"type": "REGULAR"}, 1, on_definitely_unsubmitted=lambda: refunded.append(True)
    )
    assert result is None
    assert len(session.calls) == 1
    assert refunded == []
    assert sleeps == []


def test_rate_limit_then_timeout_cannot_trigger_a_third_post(sleeps):
    session = FakeSession([FakeResponse(429, {"Retry-After": "1"}), ReadTimeout("response lost"), FakeResponse(201)])
    refunded = []
    assert api_retry.post_simulation(session, {}, 1, on_definitely_unsubmitted=lambda: refunded.append(True)) is None
    assert len(session.calls) == 2
    assert refunded == []


def test_uncertain_payload_is_logged_for_reconciliation(sleeps, caplog):
    session = FakeSession([ReadTimeout("response lost"), FakeResponse(201)])
    assert api_retry.post_simulation(session, {"regular": "rank(close)"}, 7) is None
    assert "rank(close)" in caplog.text
    assert len(session.calls) == 1


def test_client_error_is_not_retried(sleeps):
    session = FakeSession([FakeResponse(400, text="bad payload")])
    assert api_retry.post_simulation(session, {}, 1) is None
    assert len(session.calls) == 1
    assert sleeps == []
