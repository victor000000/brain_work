"""Self-correlation fetches: computed values and every fail-closed path."""

from core.api import FETCH_ERROR, get_self_correlation
from tests.test_correlation_gate_helpers import FakeResponse, FakeSession


def test_self_corr_computed_max_returned():
    session = FakeSession([FakeResponse(200, {"records": [{"corr": 0.1}], "max": 0.42})])
    assert get_self_correlation(session, "A1") == 0.42


def test_self_corr_empty_records_is_a_clean_pass():
    session = FakeSession([FakeResponse(200, {"records": [], "max": 0})])
    assert get_self_correlation(session, "A1") == 0.0


def test_self_corr_still_computing_fails_closed():
    """No `records` key while a Retry-After spin timed out → FETCH_ERROR, not 0.0."""
    session = FakeSession(
        [FakeResponse(200, {"message": "correlation is being computed"}, headers={"Retry-After": "99999"})]
    )
    assert get_self_correlation(session, "A1") == FETCH_ERROR


def test_self_corr_null_records_fails_closed():
    session = FakeSession([FakeResponse(200, {"records": None, "max": 0})])
    assert get_self_correlation(session, "A1") == FETCH_ERROR


def test_self_corr_non_numeric_max_fails_closed():
    session = FakeSession([FakeResponse(200, {"records": [{"corr": 0.1}], "max": None})])
    assert get_self_correlation(session, "A1") == FETCH_ERROR


def test_self_corr_http_error_fails_closed():
    session = FakeSession([FakeResponse(500, content=b"")])
    assert get_self_correlation(session, "A1") == FETCH_ERROR
