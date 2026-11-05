"""Recording that an alpha's check could not be decided.

Split out of `checker/auto_check_queue.py`, which re-exports `_note_deferral`.
"""

import time

from core.log import get_file_logger

rlog = get_file_logger("runner")


def _note_deferral(conn, alpha_id):
    """Record that this alpha's check could not be decided.

    The selector sends deferred alphas to the back of the queue so a congested
    one cannot monopolise a run. Best-effort: a missing table on an old DB must
    not stop the check.
    """
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    try:
        conn.execute(
            """INSERT INTO check_deferrals (alpha_id, attempts, last_at) VALUES (?, 1, ?)
               ON CONFLICT (alpha_id) DO UPDATE
                   SET attempts = check_deferrals.attempts + 1, last_at = EXCLUDED.last_at""",
            (alpha_id, now),
        )
        conn.commit()
    except Exception as e:
        rlog.debug("could not record deferral for %s: %s", alpha_id, e)
