"""Test budget checking logic."""

from unittest.mock import MagicMock

from core.budget import (
    BUDGET_FLOOR,
    check_budget,
    get_state,
    read_remaining,
    update_from_headers,
)
from tests.test_budget_helpers import isolated_budget_state  # noqa: F401


def _resp(remaining=None, limit="5000", reset="3600"):
    r = MagicMock()
    headers = {"X-Ratelimit-Limit": limit, "X-Ratelimit-Reset": reset}
    if remaining is not None:
        headers["X-Ratelimit-Remaining"] = str(remaining)
    r.headers = headers
    return r


class _FakeResponse:
    def __init__(self, headers):
        self.headers = headers


def test_returns_remaining_when_ok():
    assert check_budget(_resp(remaining=2000)) == "2000"


def test_returns_none_when_below_floor():
    assert check_budget(_resp(remaining=BUDGET_FLOOR - 1)) is None
    assert check_budget(_resp(remaining=0)) is None


def test_returns_none_when_header_missing():
    assert check_budget(_resp()) is None


def test_returns_raw_when_non_numeric():
    assert check_budget(_resp(remaining="abc")) == "abc"


def test_low_budget_still_returns():
    assert check_budget(_resp(remaining=200)) == "200"


def test_checkpoint_at_500():
    assert check_budget(_resp(remaining=500)) == "500"
    assert check_budget(_resp(remaining=1000)) == "1000"


# --------------------------------------------------------------------------
# read_remaining
# --------------------------------------------------------------------------


def test_read_remaining_parses_int():
    assert read_remaining(_FakeResponse({"X-Ratelimit-Remaining": "1234"})) == 1234


def test_read_remaining_none_when_missing():
    assert read_remaining(_FakeResponse({"X-Ratelimit-Limit": "5000"})) is None


def test_read_remaining_none_when_unparseable():
    assert read_remaining(_FakeResponse({"X-Ratelimit-Remaining": "abc"})) is None
    assert read_remaining(_FakeResponse({"X-Ratelimit-Remaining": ""})) is None


def test_read_remaining_accepts_plain_header_mapping():
    assert read_remaining({"X-Ratelimit-Remaining": "42"}) == 42


# --------------------------------------------------------------------------
# A missing header is "unknown", never "exhausted"
# --------------------------------------------------------------------------


def test_missing_header_never_marks_exhaustion():
    update_from_headers({"X-Ratelimit-Limit": "5000"})
    assert get_state().is_exhausted() is False
    update_from_headers({})
    assert get_state().is_exhausted() is False
    check_budget(_resp())
    assert get_state().is_exhausted() is False


def test_non_numeric_header_never_marks_exhaustion():
    update_from_headers({"X-Ratelimit-Remaining": "abc"})
    assert get_state().is_exhausted() is False
