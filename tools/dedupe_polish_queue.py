#!/usr/bin/env python3
"""Collapse the polish queue to one row per expression.

Polish re-simulates a near-miss under a different neutralization; the new alpha
carries the *same* expression, and if it fails one check it is queued again.
Until `storage/store_checks_polish` learned to refuse an expression already
queued, that fed itself — on 2026-10-07 the queue held 191 candidates covering
**22 expressions**, the worst 75 times over.

The cost is not bookkeeping. Each duplicate spends its own four re-runs
producing a signal already simulated, and then the copies fail
`SELF_CORRELATION` against each other: all twenty self-correlation failures
that morning were duplicates of two expressions.

Keeps the row with the most remaining budget and the earliest queue position
(lowest `attempts`, then oldest, then lowest id) and deletes the rest.

Run in the budget-exhausted window, when the explorer is idling:

    make stop
    python3 tools/dedupe_polish_queue.py --dry-run
    python3 tools/dedupe_polish_queue.py
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

DUPLICATES_SQL = """
SELECT expression, COUNT(*) AS n FROM polish_candidates GROUP BY 1 HAVING COUNT(*) > 1 ORDER BY n DESC
"""

# One survivor per expression: the one `take_batch` would reach first.
KEEPERS_SQL = """
SELECT alpha_id FROM (
    SELECT alpha_id, ROW_NUMBER() OVER (
        PARTITION BY expression ORDER BY attempts, created_at, alpha_id
    ) AS rn
    FROM polish_candidates
) WHERE rn = 1
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report, change nothing")
    args = ap.parse_args()

    conn = connect(DB_PATH)
    try:
        dupes = conn.execute(DUPLICATES_SQL).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0]
        keepers = conn.execute(f"SELECT COUNT(*) FROM ({KEEPERS_SQL})").fetchone()[0]
        for expr, n in dupes[:8]:
            print(f"  {n:3d}x  {str(expr)[:88]}")
        if len(dupes) > 8:
            print(f"  ... and {len(dupes) - 8} more duplicated expressions")
        print(f"\n{total} candidates covering {keepers} distinct expressions")
        if not dupes:
            return 0
        if args.dry_run:
            print(f"would delete {total - keepers} duplicate row(s)")
            return 0

        conn.execute(f"DELETE FROM polish_candidates WHERE alpha_id NOT IN ({KEEPERS_SQL})")
        conn.commit()
        left = conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0]
        print(f"deleted {total - left} duplicate row(s); {left} remain")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
