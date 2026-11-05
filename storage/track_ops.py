"""Track which operators are used in successful alpha expressions."""

import re

from core.log import get_file_logger

olog = get_file_logger("ops")


def _operators(expression):
    return set(re.findall(r"([a-z_]+)\s*\(", expression or ""))


def _ensure_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS operator_usage "
        "(operator TEXT, region TEXT, count INT DEFAULT 0, "
        "PRIMARY KEY (operator, region))"
    )


def track_operator_usage(conn, expression, region):
    """Record each operator found in a successful expression."""
    _ensure_table(conn)
    operators = _operators(expression)
    for op in operators:
        conn.execute(
            "INSERT INTO operator_usage VALUES (?,?,1) ON CONFLICT(operator,region) DO UPDATE SET count=count+1",
            (op, region),
        )
    olog.debug("SUCCESS %s: %s", region, sorted(operators))


def untrack_operator_usage(conn, expression, region):
    """Remove the operators previously credited to `expression` in `region`.

    Mirrors track_operator_usage so a re-store of the same alpha does not
    double-count (store_alpha calls untrack for the old row, then track for
    the new one).
    """
    _ensure_table(conn)
    operators = _operators(expression)
    for op in operators:
        conn.execute(
            "UPDATE operator_usage SET count=count-1 WHERE operator=? AND region=?",
            (op, region),
        )
        conn.execute(
            "DELETE FROM operator_usage WHERE operator=? AND region=? AND count<=0",
            (op, region),
        )
    olog.debug("UNTRACK %s: %s", region, sorted(operators))
