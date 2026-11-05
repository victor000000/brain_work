"""FIX 3: Retry-After parsing never raises, handles HTTP-dates and junk."""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from runner.http_retry import parse_retry_after, retry_after_or


def test_numeric_seconds():
    assert parse_retry_after({"Retry-After": "12"}) == 12.0
    assert parse_retry_after({"Retry-After": "2.5"}) == 2.5
    assert parse_retry_after({"Retry-After": "0"}) == 0.0


def test_http_date_future():
    when = datetime.now(UTC) + timedelta(seconds=30)
    value = parse_retry_after({"Retry-After": format_datetime(when)})
    assert value is not None
    assert 25 <= value <= 31


def test_http_date_past_is_zero():
    when = datetime.now(UTC) - timedelta(seconds=30)
    assert parse_retry_after({"Retry-After": format_datetime(when)}) == 0.0


def test_junk_and_missing_never_raise():
    assert parse_retry_after({}) is None
    assert parse_retry_after({"Retry-After": "not-a-date"}) is None
    assert parse_retry_after({"Retry-After": "nan"}) is None
    assert parse_retry_after({"Retry-After": "inf"}) is None
    assert parse_retry_after(None) is None


def test_retry_after_or_defaults():
    assert retry_after_or({"Retry-After": "4"}, default=10.0) == 4.0
    assert retry_after_or({}, default=10.0) == 10.0
    assert retry_after_or({"Retry-After": "junk"}, default=10.0) == 10.0
