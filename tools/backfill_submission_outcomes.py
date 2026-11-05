"""One-time backfill of submission_outcomes from alpha_results.status='SUBMITTED'.

Historical bug: tools/reconcile_submissions.py flipped status to SUBMITTED
via direct UPDATE without calling _record_outcome, leaving 7 rows where
status='SUBMITTED' but submission_outcomes.submitted=0 for the matching cell.

This script idempotently bumps the counter once per cell-with-SUBMITTED-alpha
that hasn't already been credited. Run once after the reconcile fix lands.

Idempotency:
  We count how many submission_outcomes.submitted units are owed per cell
  (= count of SUBMITTED alphas in that cell) and how many already exist
  (= submission_outcomes.submitted). Backfill makes up the delta.
"""

from core.db import Connection, get_conn
from runner.submit.outcome import _record_outcome


def run_backfill(conn: Connection) -> int:
    """Bump submission_outcomes.submitted to match the count of SUBMITTED
    alphas per cell, where it currently lags. Returns the total number of
    bumps performed.
    """
    submitted_alphas = conn.execute(
        """
        SELECT alpha_id, template, region, universe, delay, neutralization
        FROM alpha_results
        WHERE status = 'SUBMITTED' AND template IS NOT NULL
        """
    ).fetchall()
    submitted_per_cell: dict = {}
    aid_by_cell: dict = {}
    for aid, t, r, u, d, n in submitted_alphas:
        key = (t, r, u, d, n)
        submitted_per_cell[key] = submitted_per_cell.get(key, 0) + 1
        aid_by_cell.setdefault(key, []).append(aid)

    existing = {
        (t, r, u, d, n): s
        for t, r, u, d, n, s in conn.execute(
            "SELECT template, region, universe, delay, neutralization, submitted FROM submission_outcomes"
        ).fetchall()
    }

    total_bumps = 0
    for key, owed in submitted_per_cell.items():
        already = existing.get(key, 0)
        delta = owed - already
        for _ in range(delta):
            _record_outcome(conn, aid_by_cell[key][0], "SUBMITTED")
            total_bumps += 1
    return total_bumps


def main():
    conn = get_conn()
    n = run_backfill(conn)
    print(f"Backfilled {n} submission_outcomes.submitted bumps")


if __name__ == "__main__":
    main()
