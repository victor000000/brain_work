"""Status-only updates to the `simulations` table.

Split out of `storage/store_sim.py`, which re-exports both names so the poll
loops keep their `from storage.store_sim import update_sim_status`.
"""

_KEEP_ERROR = object()


def update_sim_status(conn, sim_id, status, error_msg=_KEEP_ERROR, ts=None):
    """Update only the status/error columns of an existing simulations row.

    Used by the poll loop to mark a parent batch COMPLETE/ERROR/ABORTED without
    clobbering the expression/settings stored at submit time. Pass error_msg=None
    to clear a stale error; omit it to leave the stored message untouched.
    """
    if error_msg is _KEEP_ERROR:
        conn.execute(
            "UPDATE simulations SET status=?, completed_at=COALESCE(?, completed_at) WHERE sim_id=?",
            (status, ts, sim_id),
        )
    else:
        conn.execute(
            "UPDATE simulations SET status=?, error_message=?, completed_at=COALESCE(?, completed_at) WHERE sim_id=?",
            (status, error_msg, ts, sim_id),
        )
    conn.commit()
