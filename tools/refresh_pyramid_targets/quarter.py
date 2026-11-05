"""Calendar-quarter bounds — matches the BRAIN dashboard period selector."""

import datetime as _dt


def quarter_bounds(today=None):
    """Return (start_iso, end_iso) for the calendar quarter containing `today`."""
    if today is None:
        today = _dt.datetime.now(_dt.UTC).date()  # UTC, like every other stamp in the project
    q = (today.month - 1) // 3
    start = _dt.date(today.year, 3 * q + 1, 1)
    end_month = 3 * q + 3
    if end_month == 12:
        end = _dt.date(today.year, 12, 31)
    else:
        end = _dt.date(today.year, end_month + 1, 1) - _dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()
