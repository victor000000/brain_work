"""Offset and bare UTC text denote the same instant in every session time zone."""

import pytest

from core.db import connect
from core.time_sql import utc_timestamp_sql


@pytest.mark.parametrize("zone", ["UTC", "Asia/Shanghai", "America/New_York"])
@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-10-16T11:08:34-04:00", "2026-10-16 15:08:34"),
        ("2026-10-17T00:08:34+0900", "2026-10-16 15:08:34"),
        ("2026-10-16T15:08:34Z", "2026-10-16 15:08:34"),
        ("2026-10-16 15:08:34 UTC", "2026-10-16 15:08:34"),
        ("2026-10-16 15:08:34", "2026-10-16 15:08:34"),
        ("2026-10-16", "2026-10-16 00:00:00"),
        ("2026-11-01T01:30:00-04:00", "2026-11-01 05:30:00"),
        ("2026-11-01T01:30:00-05:00", "2026-11-01 06:30:00"),
        (None, None),
        ("not a timestamp", None),
    ],
)
def test_timestamp_is_utc_without_a_python_timezone_dependency(zone, value, expected):
    conn = connect(":memory:")
    try:
        conn.execute("SET TimeZone = ?", [zone])
        row = conn.execute(
            f"SELECT strftime({utc_timestamp_sql('stamp')}, '%Y-%m-%d %H:%M:%S') FROM (VALUES (?)) AS input(stamp)",
            [value],
        ).fetchone()
        assert row == (expected,)
    finally:
        conn.close()
