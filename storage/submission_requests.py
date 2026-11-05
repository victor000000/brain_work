"""Durable ownership of submission requests whose outcome is still unknown."""

import time


def _ensure_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS submission_requests ("
        "alpha_id TEXT PRIMARY KEY, state TEXT NOT NULL, created_at TEXT NOT NULL, http_status INTEGER)"
    )


def needs_reconciliation(conn, alpha_id):
    """A pending or verified request must be observed, never posted again."""
    exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='submission_requests'"
    ).fetchone()
    if not exists or exists[0] != 1:
        return False
    row = conn.execute("SELECT state FROM submission_requests WHERE alpha_id=?", (alpha_id,)).fetchone()
    return bool(row and row[0] in ("PENDING", "VERIFIED"))


def begin_request(conn, alpha_id, *, http_status=None):
    """Commit intent before POST; a crash or timeout leaves ownership durable.

    Also supports recovering a known HTTP201 receipt from an earlier runner.
    Failure to persist propagates before any network mutation is attempted.
    """
    _ensure_table(conn)
    row = conn.execute(
        "INSERT INTO submission_requests VALUES (?, 'PENDING', ?, ?) "
        "ON CONFLICT (alpha_id) DO UPDATE SET state='PENDING', http_status=EXCLUDED.http_status "
        "WHERE submission_requests.state='REJECTED' RETURNING alpha_id",
        (alpha_id, time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), http_status),
    ).fetchone()
    conn.commit()
    return row is not None


def record_response(conn, alpha_id, http_status):
    """Only an explicit rejection/throttle releases the request for retry."""
    state = "REJECTED" if http_status in (403, 429) else "PENDING"
    conn.execute(
        "UPDATE submission_requests SET state=?, http_status=? WHERE alpha_id=?",
        (state, http_status, alpha_id),
    )
    conn.commit()


def mark_verified(conn, alpha_id):
    conn.execute("UPDATE submission_requests SET state='VERIFIED' WHERE alpha_id=?", (alpha_id,))
    conn.commit()
