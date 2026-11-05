#!/usr/bin/env python3
"""Reconcile alpha status against BRAIN's ground truth.

For each row whose local status is transient (UNSUBMITTED, THROTTLED),
GET /alphas/{id} and flip to SUBMITTED if dateSubmitted is set on BRAIN.
Bounded by eligibility filter so we don't sweep the entire 78k-row table.
"""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

# Runnable both as `python3 tools/reconcile_submissions.py` and `python3 -m tools.reconcile_submissions`.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.auth import get_session
from core.db import get_conn
from core.log import get_file_logger
from runner.submit.eligibility import build_eligibility_union
from runner.submit.outcome import _record_outcome

API = "https://api.worldquantbrain.com"
clog = get_file_logger("check")

PACE_SEC = 0.3  # 300ms between GETs


def main():
    conn = get_conn()
    sess = get_session()

    rows = conn.execute(f"""
        SELECT alpha_id FROM alpha_results
         WHERE {build_eligibility_union()}
           AND (status IS NULL OR status IN ('UNSUBMITTED', 'THROTTLED'))
        ORDER BY is_sharpe DESC
    """).fetchall()

    ids = [r[0] for r in rows]
    print(f"Reconciling {len(ids)} transient-status eligible alphas...")
    clog.info("Reconcile start: %d alphas", len(ids))

    landed, errors = [], []
    for i, aid in enumerate(ids, start=1):
        try:
            r = sess.get(f"{API}/alphas/{aid}", timeout=20)
        except Exception as e:
            errors.append((aid, f"exc:{e}"))
            continue

        if r.status_code != 200:
            errors.append((aid, f"HTTP {r.status_code}"))
            time.sleep(PACE_SEC)
            continue

        ds = r.json().get("dateSubmitted")
        if ds:
            landed.append((aid, ds))
            with conn:
                conn.execute("UPDATE alpha_results SET status='SUBMITTED' WHERE alpha_id=?", (aid,))
                _record_outcome(conn, aid, "SUBMITTED")
            print(f"  [{i}/{len(ids)}] {aid} -> SUBMITTED ({ds})")
        time.sleep(PACE_SEC)

    print(f"\n=== Reconcile: {len(landed)} flipped to SUBMITTED, {len(errors)} errors ===")
    clog.info("Reconcile done: %d flipped, %d errors", len(landed), len(errors))
    if errors[:10]:
        print("First errors:", errors[:10])

    conn.close()


if __name__ == "__main__":
    main()
