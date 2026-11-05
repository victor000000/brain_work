"""Delay parsing: seconds, RFC-7231 dates, and hostile numeric values."""


def test_parse_delay_accepts_seconds_and_dates():
    from download.session_throttle import _parse_delay

    assert _parse_delay("12") == 12.0
    assert _parse_delay(" 2.5 ") == 2.5
    assert _parse_delay(None) is None
    assert _parse_delay("") is None
    assert _parse_delay("garbage") is None
    assert _parse_delay("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0  # long past


# ── Hostile / malformed numeric header values ─────────────────────
#
# `RateLimit-Reset: 1e400` parsed to inf, `_adapt` stored it as the interval,
# and the next `_throttle` did `time.sleep(inf - gap)` -> OverflowError, which
# BrainSession.get does not catch. Huge finite values (1e23) and negative
# values are in the same family; the parse must stay finite and bounded.


def test_parse_delay_rejects_non_finite():
    from download.session_throttle import _parse_delay

    for raw in ("inf", "Inf", "Infinity", "-inf", "nan", "NaN", "1e400", "1e309", "-1e400"):
        assert _parse_delay(raw) is None, raw


def test_parse_delay_caps_huge_finite_values():
    from download.session_throttle import MAX_RETRY_SLEEP, _parse_delay

    assert _parse_delay("9" * 30) == MAX_RETRY_SLEEP
    assert _parse_delay("1e23") == MAX_RETRY_SLEEP
    assert _parse_delay("99999") == MAX_RETRY_SLEEP


def test_parse_delay_negative_is_zero():
    from download.session_throttle import _parse_delay

    assert _parse_delay("-1") == 0.0
    assert _parse_delay("-1e400") is None  # non-finite before the clamp


def test_parse_delay_far_future_date_is_capped():
    from download.session_throttle import MAX_RETRY_SLEEP, _parse_delay

    assert _parse_delay("Fri, 31 Dec 9999 23:59:59 GMT") == MAX_RETRY_SLEEP
