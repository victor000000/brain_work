#!/usr/bin/env python3
"""System health check — validates all components are working.

CLI: `python3 -m tools.healthcheck` (also wired up via `make health`).

Exit status is non-zero when any check fails, so CI and `make health` can gate
on it.
"""

import os
import sys

from core.db import OperationalError, connect_for_reading
from tools.healthcheck.checks import (
    check,
    check_alpha_recency,
    check_database,
    check_explorer_progress,
    check_field_freshness,
    check_generator,
    check_integrity,
    check_processes,
    check_results,
    check_scope,
    check_templates,
)

# After the move into tools/healthcheck/, __file__ is two levels under the
# project root; resolve absolute paths once.
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(_HERE))
DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")
from core.log_config import LOG_DIR  # noqa: E402  (single definition)


def _run(name, fn, *args, ok=True):
    """Run one check function, converting an exception into a failed check."""
    try:
        return ok & fn(*args)
    except Exception as err:
        return check(name, False, f"raised {type(err).__name__}: {err}")


def main():
    print("=== BRAIN Alpha Generator Health Check ===\n")

    if not os.path.exists(DB_PATH):
        print(f"[FAIL] no database at {DB_PATH}")
        print(f"\n{'=' * 40}")
        print("SOME CHECKS FAILED")
        return 1

    ok = True
    conn = None
    try:
        # The explorer holds DuckDB's single write lock while it runs, and this
        # check has a "processes: explorer running" step — it is meant to be run
        # *during* operation. So a lock conflict is an ordinary state to report,
        # not a crash: the checks that need no database still run.
        try:
            conn = connect_for_reading(DB_PATH)
        except OperationalError as err:
            print(f"[SKIP] database is not readable right now: {str(err)[:90]}")
            print("       (the explorer holds the write lock; the checks below need no database)\n")

        if conn is not None:
            ok &= _run("database", check_database, conn)
            ok &= _run("integrity", check_integrity, conn)
            ok &= _run("scope", check_scope, conn)
            ok &= _run("field freshness", check_field_freshness, conn)
        ok &= _run("templates", check_templates)
        if conn is not None:
            ok &= _run("generator", check_generator, conn)
            ok &= _run("results", check_results, conn)
            ok &= _run("alpha recency", check_alpha_recency, conn)
            ok &= _run("explorer progress", check_explorer_progress, conn)
        ok &= _run("processes", check_processes)
    finally:
        if conn is not None:
            conn.close()

    # Log files check — point at the project's brain_logs/, not the project root.
    print("\n[Logs]")
    log_count = len([f for f in os.listdir(LOG_DIR) if f.endswith(".log")]) if os.path.isdir(LOG_DIR) else 0
    ok &= check("Log files", log_count >= 10, f"{log_count} log files")

    print(f"\n{'=' * 40}")
    print(f"{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
