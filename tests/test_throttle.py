"""Rate-limit throttling.

Learned from ACE (`vendor/ace_api/extracted/ace_lib.py:_check_rate_limit`),
WorldQuant's own toolkit: it reads **both** the per-second and the per-minute
budget. Ours read only the minute header, which is why the refresh burst past
the 1 req/s cap and collected 429s.
"""

from download.session_throttle import MIN_INTERVAL
from tests.test_throttle_helpers import Host, Resp


def test_no_rate_headers_leaves_interval_alone():
    h = Host()
    before = h._interval
    h._adapt(Resp())
    assert h._interval == before


def test_healthy_budgets_use_the_floor():
    h = Host()
    h._interval = 99.0
    h._adapt(Resp({"X-RateLimit-Remaining-Minute": "30", "X-RateLimit-Limit-Minute": "30"}))
    assert h._interval == MIN_INTERVAL


def test_second_budget_exhausted_forces_at_least_a_second():
    """One request per second is a hard cap; exceeding it yields 429s."""
    h = Host()
    h._adapt(
        Resp(
            {
                "X-RateLimit-Remaining-Minute": "30",
                "X-RateLimit-Limit-Minute": "30",
                "X-RateLimit-Remaining-Second": "0",
            }
        )
    )
    assert h._interval >= 1.0


def test_second_budget_available_keeps_the_floor():
    h = Host()
    h._adapt(
        Resp(
            {
                "X-RateLimit-Remaining-Minute": "30",
                "X-RateLimit-Limit-Minute": "30",
                "X-RateLimit-Remaining-Second": "1",
            }
        )
    )
    assert h._interval == MIN_INTERVAL


def test_low_minute_budget_slows_down():
    h = Host()
    h._adapt(Resp({"X-RateLimit-Remaining-Minute": "5", "X-RateLimit-Limit-Minute": "30"}))
    assert h._interval > MIN_INTERVAL


def test_exhausted_minute_budget_backs_off_hard():
    h = Host()
    h._adapt(
        Resp(
            {
                "X-RateLimit-Remaining-Minute": "0",
                "X-RateLimit-Limit-Minute": "30",
                "RateLimit-Reset": "30",
            }
        )
    )
    assert h._interval >= 30


def test_thresholds_derive_from_the_limit_not_hardcoded():
    """Thresholds are proportional, not absolute.

    15 requests left is half of a 30/min budget but only a quarter of a
    60/min one, so the larger budget should already be backing off while the
    smaller one still runs at full speed.
    """
    h30, h60 = Host(), Host()
    h30._adapt(Resp({"X-RateLimit-Remaining-Minute": "15", "X-RateLimit-Limit-Minute": "30"}))
    h60._adapt(Resp({"X-RateLimit-Remaining-Minute": "15", "X-RateLimit-Limit-Minute": "60"}))
    assert h30._interval <= h60._interval
