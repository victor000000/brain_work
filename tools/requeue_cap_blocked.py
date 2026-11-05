#!/usr/bin/env python3
"""Re-queue alphas retired by the submission cap, and drop their polish rows.

`REGULAR_SUBMISSION` fails on every alpha once the account's four submissions
for the period are spent (`limit=4 val=4`) — it is a property of the account,
not of the alpha. Before `checker/auto_check_alpha` learned to defer on it
(2026-10-07 00:16 UTC) and before `storage/store_checks` refused to summarise
it, a check run stored the cap as the alpha's one failing check. That wrote an
`alpha_check_summary` row, and the summary is the auto-checker's "already
checked" filter: the alpha is excluded from every later run, so it can never be
submitted even after the cap lifts.

51 alphas were retired that way between 20:48 (the fourth accepted alpha) and
the fix. Every one passes the other checks — they are the most submission-ready
alphas the account has, and they are invisible to the pipeline.

Two repairs, both keyed on the same premise:

* Delete the summary row. The alpha returns to the check queue, which costs a
  preview GET and no simulation budget, and submits once the cap lifts.
* Delete the polish row. Polish re-simulates a one-failure alpha under other
  settings, which cannot fix an account-wide cap; leaving the rows there spends
  simulation budget on the only failure settings cannot change.

The check rows and `check_failures` history are kept: they are the record of
what was observed, and the next check replaces them wholesale.

Run in the budget-exhausted window, when the explorer is idling and a stop
costs no simulations:

    make stop
    python3 tools/requeue_cap_blocked.py --dry-run
    python3 tools/requeue_cap_blocked.py
    make start
"""

import argparse
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.db import connect  # noqa: E402

DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")

# The alphas the cap retired: one failing check in total, and that check is the
# cap. `submission_checks` is replaced wholesale on every check, so it always
# describes the newest response.
RETIRED_SQL = """
SELECT s.alpha_id, a.is_sharpe, a.region, a.universe
FROM alpha_check_summary s
JOIN alpha_results a ON a.alpha_id = s.alpha_id
WHERE s.fail_count = 1
  AND a.status NOT IN ('SUBMITTED', 'REJECTED')
  AND (SELECT COUNT(*) FROM submission_checks c
       WHERE c.alpha_id = s.alpha_id AND c.result = 'FAIL') = 1
  AND EXISTS (SELECT 1 FROM submission_checks c
              WHERE c.alpha_id = s.alpha_id AND c.result = 'FAIL'
                AND c.check_name = 'REGULAR_SUBMISSION')
ORDER BY a.is_sharpe DESC
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report, change nothing")
    args = ap.parse_args()

    conn = connect(DB_PATH)
    try:
        rows = conn.execute(RETIRED_SQL).fetchall()
        for alpha_id, sharpe, region, universe in rows:
            print(f"  {alpha_id}  sh={sharpe:.2f}  {region}/{universe}")
        print(f"\n{len(rows)} alphas retired by the cap alone")
        if not rows:
            return 0
        if args.dry_run:
            print("dry run — nothing changed")
            return 0

        ids = [(r[0],) for r in rows]
        conn.executemany("DELETE FROM alpha_check_summary WHERE alpha_id = ?", ids)
        # `polish_candidates` may hold rows from before the cap was reached;
        # the premise is judged on the newest check, which is the cap alone.
        conn.executemany("DELETE FROM polish_candidates WHERE alpha_id = ?", ids)
        conn.commit()
        print(f"re-queued {len(rows)} alphas; dropped their polish rows")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
