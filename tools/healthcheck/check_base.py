"""The reporting primitive and timestamp parsing shared by every health check.

Split out of `tools/healthcheck/checks.py`, which re-exports `check` and
`_count` — `__main__.py` imports `check` from there.
"""

from datetime import UTC, datetime

from tools.healthcheck.thresholds import _TS_FORMATS


def check(name, condition, detail=""):
    """Print check result and return condition."""
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return condition


def _count(conn, sql):
    return conn.execute(sql).fetchone()[0]


def _parse_utc(text):
    """Parse a stored timestamp ('... UTC' or bare), returning a POSIX time or None."""
    if not text:
        return None
    for fmt in _TS_FORMATS:
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=UTC)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def _parse_iso(text):
    """Parse an ISO-8601 timestamp (with or without offset) to a POSIX time."""
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()
