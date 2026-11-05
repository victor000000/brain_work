#!/usr/bin/env python3
"""One-line alpha summary for `make status`.

DuckDB allows a single process per database, so while the explorer is running
this cannot open the file at all; that is reported plainly rather than as a
traceback.
"""

import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.db import DB_PATH, OperationalError, connect  # noqa: E402


def main():
    try:
        conn = connect(DB_PATH)
    except OperationalError:
        print("Alphas: unavailable — the explorer holds the database")
        return 0
    try:
        total = conn.execute("SELECT COUNT(*) FROM alpha_results").fetchone()[0]
        positive = conn.execute("SELECT COUNT(*) FROM alpha_results WHERE is_sharpe > 0").fetchone()[0]
    finally:
        conn.close()
    print(f"Alphas: {total:,} total, {positive:,} positive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
