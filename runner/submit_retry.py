"""Retry bookkeeping for submission checks the platform would not decide.

Split out of `runner/submit_checks.py`, which re-exports both helpers: the
retry count decides when an undecided check is given up on, and the marker row
keeps a store_checks(write_summary=False) alpha in the auto-checker's queue.
"""

import time

# Rounds the platform may leave a submit undecided before we stop POSTing it.
# Both undecided outcomes count against it: a 403 carrying ERROR/PENDING, and a
# `201` that never sets `dateSubmitted`. The second was missed on 2026-10-07 —
# it incremented the count but nothing read it on that path, so `vR2jeq9G`
# collected six void 201s and the rest of the queue paid for them.
MAX_SUBMIT_ROUNDS = 5

# How long a spent count holds an alpha back before it may be POSTed again.
#
# The count bounds the *loop* — an alpha the platform will not decide must not
# head every check run — but it must not become a retirement, and for a while
# it was one: the gate compared the count to MAX_SUBMIT_ROUNDS and nothing ever
# lowered it, so the first five undecided rounds barred the alpha from being
# submitted ever again. What leaves a submit undecided is platform state, not
# the alpha: a 403 ERROR/PENDING is the platform failing to run a check, and
# the void `201` was measured while an account-wide quota was spent, where a
# submit is answered without being performed. Both clear on their own, and
# `runner.verify_submit` already says as much where it counts them — "never
# retire it, because nothing here says anything about the alpha".
#
# Measured 2026-10-08, before this cooldown existed: all 32 alphas holding a
# spent count had reached it on 2026-10-07, and every one of them passes
# `REGULAR_SUBMISSION` and every other check — their only FAIL was
# `POWER_POOL_SUBMISSION` (limit 1, flagging the account's allowance). They
# were permanently barred by a quota that had already reset.
#
# The same window as `checker.auto_check_queue.DEFERRAL_BACKOFF_SEC`, and
# deliberately: a give-up defers the alpha, which already keeps it out of the
# selector for that long, so aligning the two gives one POST per window rather
# than a POST on every run the deferral lets through.
SUBMIT_ROUND_COOLDOWN_SEC = 6 * 3600


def _cooldown_cutoff():
    """The `last_seen` at which a spent count stops barring the next POST.

    Formatted exactly as `_increment_retry_count` writes it: the column is TEXT
    and the comparison is lexicographic, so a differently shaped string would
    compare confidently and wrongly rather than raise.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() - SUBMIT_ROUND_COOLDOWN_SEC))


def _cooling_submit_rounds(conn, alpha_id):
    """Spent submit rounds while they still bar a POST; 0 when it may submit.

    Returns the count rather than a bool so the caller can log it: the gate
    used to report a hardcoded `MAX_SUBMIT_ROUNDS`, which read as a constant
    state rather than a tally that keeps climbing. The count is not reset when
    the cooldown lapses — it is a running tally of undecided rounds over the
    alpha's life, and `SUBMIT_ROUND_COOLDOWN_SEC` is what gates, not the total.
    """
    row = conn.execute(
        "SELECT seen_count, last_seen FROM check_failures WHERE alpha_id = ? AND check_name = 'RETRY_ATTEMPT'",
        (alpha_id,),
    ).fetchone()
    if not row or (row[0] or 0) < MAX_SUBMIT_ROUNDS:
        return 0
    return row[0] if (row[1] or "") > _cooldown_cutoff() else 0


def _get_retry_count(conn, alpha_id):
    """Rounds this alpha has been submitted and left undecided.

    Reads the marker `_increment_retry_count` writes. It previously read the
    `seen_count` of the *check* rows instead — a set that does not contain
    `RETRY_ATTEMPT`, so the increment was never observed, the count stayed 0 and
    the give-up branch was unreachable. Verified 2026-10-07: no `GIVING UP` line
    in any log, and the warning printed `retry 1/5` on every round.
    """
    row = conn.execute(
        "SELECT seen_count FROM check_failures WHERE alpha_id = ? AND check_name = 'RETRY_ATTEMPT'",
        (alpha_id,),
    ).fetchone()
    return row[0] if row and row[0] else 0


def _increment_retry_count(conn, alpha_id):
    """Record one undecided submit round; return the new count."""
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    conn.execute(
        """INSERT INTO check_failures
               (alpha_id, check_name, limit_val, actual_val, first_seen, last_seen, seen_count)
           VALUES (?, 'RETRY_ATTEMPT', NULL, NULL, ?, ?, 1)
           ON CONFLICT (alpha_id, check_name) DO UPDATE SET
               last_seen = EXCLUDED.last_seen,
               seen_count = check_failures.seen_count + 1""",
        (alpha_id, now, now),
    )
    conn.commit()
    return _get_retry_count(conn, alpha_id)
