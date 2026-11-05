"""Correlation gate must fail CLOSED.

The old leak: a self-correlation poll that timed out returned an in-progress
body, `records` was missing, and the code read that as 0.0 — a clean pass.
"""

from core.api import FETCH_ERROR, NOT_ELIGIBLE, _corr_passes, check_correlation_gate
from tests.test_correlation_gate_helpers import FakeResponse, FakeSession


def test_corr_passes_fails_closed_on_missing_or_non_numeric():
    assert _corr_passes(None, 0.7) is False
    assert _corr_passes("0.1", 0.7) is False  # numeric-looking string is not a result
    assert _corr_passes(float("nan"), 0.7) is False
    assert _corr_passes(FETCH_ERROR, 0.7) is False


def test_corr_passes_sentinels_and_numbers():
    assert _corr_passes(0.1, 0.7) is True
    assert _corr_passes(0.9, 0.7) is False
    assert _corr_passes(NOT_ELIGIBLE, 0.7) is True


def test_gate_fails_closed_when_self_corr_still_computing():
    prod = FakeResponse(412, content=b"")  # not eligible → pass
    self_in_progress = FakeResponse(200, {"message": "computing"}, headers={"Retry-After": "99999"})
    session = FakeSession([prod, self_in_progress])
    passes, details = check_correlation_gate(session, "A1")
    assert passes is False
    assert details["self"] == FETCH_ERROR


def test_gate_passes_with_clean_self_corr_and_ineligible_prod():
    prod = FakeResponse(412, content=b"")
    self_ok = FakeResponse(200, {"records": [{"corr": 0.1}], "max": 0.1})
    session = FakeSession([prod, self_ok])
    passes, details = check_correlation_gate(session, "A1")
    assert passes is True
    assert details == {"prod": NOT_ELIGIBLE, "self": 0.1}
