"""Detect a connection that cannot safely support explorer work."""


class UnusableConnectionError(RuntimeError):
    """The process must release its connection before a supervisor retry."""


def require_usable_connection(conn):
    """After a loader failure, distinguish bad metadata from a dead connection."""
    try:
        conn.execute("SELECT 1").fetchone()
    except Exception as error:
        raise UnusableConnectionError("Database health query failed; refusing explorer startup") from error
