#!/usr/bin/env python3
"""Check all positive alphas for submission, auto-submit if all pass."""

import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

# Runnable both as `python3 tools/check_alphas.py` and `python3 -m tools.check_alphas`.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.auth import get_session
from core.db import get_conn, init_tables
from core.log import get_file_logger
from runner.submit import check_and_submit
from runner.submit.eligibility import build_eligibility_union

clog = get_file_logger("check")


def main():
    conn = get_conn()
    init_tables(conn)
    session = get_session()

    rows = conn.execute(f"""
        SELECT alpha_id, region, universe, delay, is_sharpe, test_sharpe
        FROM alpha_results
        WHERE {build_eligibility_union()}
          AND alpha_id NOT IN (SELECT alpha_id FROM alpha_check_summary)
        ORDER BY is_sharpe DESC
    """).fetchall()

    clog.info("Checking %d alphas for submission...", len(rows))
    print(f"Checking {len(rows)} alphas...")
    submitted = []

    for i, (aid, reg, uni, dly, sh, tsh) in enumerate(rows):
        time.sleep(0.5)
        result = check_and_submit(session, conn, aid)

        if result == "SUBMITTED":
            submitted.append(aid)

        if i < 20 or "SUBMIT" in result or result.startswith("FAIL:1"):
            print(f"  {aid} {reg}/{uni}/d{dly} sh={sh:.2f} ts={tsh:.2f} -> {result}")

    clog.info("DONE: %d checked, %d submitted", len(rows), len(submitted))
    print(f"\n=== {len(rows)} checked, {len(submitted)} submitted ===")
    if submitted:
        clog.warning("SUBMITTED: %s", submitted)
        print("Submitted:", submitted)

    # Fail summary
    print("\nFail reasons:")
    for n, c in conn.execute(
        "SELECT check_name, COUNT(*) FROM submission_checks "
        "WHERE result='FAIL' GROUP BY check_name ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"  {n}: {c}")

    conn.close()


if __name__ == "__main__":
    main()
