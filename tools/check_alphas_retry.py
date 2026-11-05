#!/usr/bin/env python3
"""Retry submittable alphas with throttle-aware exponential backoff.

Selects eligible alphas whose status is still transient (UNSUBMITTED, THROTTLED,
or absent). Terminal statuses (SUBMITTED, REJECTED) are skipped.
"""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

# Runnable both as `python3 tools/check_alphas_retry.py` and `python3 -m tools.check_alphas_retry`.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.auth import get_session
from core.db import get_conn, init_tables
from core.log import get_file_logger
from runner.submit import check_and_submit
from runner.submit.eligibility import build_eligibility_union

clog = get_file_logger("check")


# Exponential throttle backoff: 60s, 120s, 300s — then give up on this alpha.
THROTTLE_BACKOFF = (60, 120, 300)
NORMAL_GAP = 3  # seconds between successful checks


def _retry_one(session, conn, aid, reg, uni, dly, sh, tsh, idx, total):
    """Run one alpha through check_and_submit with bounded throttle backoff.

    Returns the final outcome string, or "THROTTLE_GAVE_UP" if all backoff
    attempts hit 429.
    """
    for attempt, pause in enumerate(THROTTLE_BACKOFF, start=1):
        result = check_and_submit(session, conn, aid)
        if result != "THROTTLED":
            return result
        is_last = attempt == len(THROTTLE_BACKOFF)
        suffix = "giving up" if is_last else f"waiting {pause}s"
        print(f"  [{idx}/{total}] {aid} {reg}/{uni}/d{dly} sh={sh:.2f} -> THROTTLED (attempt {attempt}, {suffix})")
        if is_last:
            return "THROTTLE_GAVE_UP"
        time.sleep(pause)
    return "THROTTLE_GAVE_UP"  # unreachable, satisfies linter


def main():
    conn = get_conn()
    init_tables(conn)
    session = get_session()

    rows = conn.execute(f"""
        SELECT alpha_id, region, universe, delay, is_sharpe, test_sharpe
        FROM alpha_results
        WHERE {build_eligibility_union()}
          AND (status IS NULL OR status IN ('UNSUBMITTED', 'THROTTLED'))
        ORDER BY is_sharpe DESC
    """).fetchall()

    clog.info("Retry-checking %d alphas for submission...", len(rows))
    print(f"Checking {len(rows)} eligible-non-terminal alphas (throttle-aware)...")

    submitted = []
    gave_up = 0
    for i, (aid, reg, uni, dly, sh, tsh) in enumerate(rows, start=1):
        result = _retry_one(session, conn, aid, reg, uni, dly, sh, tsh, i, len(rows))

        if result == "SUBMITTED":
            submitted.append(aid)
        if result == "THROTTLE_GAVE_UP":
            gave_up += 1

        print(f"  [{i}/{len(rows)}] {aid} {reg}/{uni}/d{dly} sh={sh:.2f} ts={tsh:.2f} -> {result}")
        time.sleep(NORMAL_GAP)

    clog.info("DONE: %d checked, %d submitted, %d gave up", len(rows), len(submitted), gave_up)
    print(f"\n=== {len(rows)} checked, {len(submitted)} submitted, {gave_up} gave up to throttle ===")
    if submitted:
        clog.warning("SUBMITTED: %s", submitted)
        print("Submitted:", submitted)

    conn.close()


if __name__ == "__main__":
    main()
