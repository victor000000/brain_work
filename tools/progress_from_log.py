#!/usr/bin/env python3
"""Progress summary for one day, read from the logs rather than the database.

DuckDB allows a single process per file, so while the explorer is running
`tools/db_status` cannot open `brain_data.duckdb` at all and `make status` has
nothing to show. The logs are appended in real time, so they answer the same
question — how many alphas, how good, in which cells — with no lock contention.

Sources:
  brain_logs/alpha.log[.<date>]   one `[INFO] log_alpha` line per stored alpha
  brain_logs/check.log[.<date>]   `store_checks` lines: pass/fail per check
  brain_logs/errors.log[.<date>]  batches the platform wrote off

The line patterns, the parser and the report live in `progress_from_log_patterns`,
`progress_from_log_collect` and `progress_from_log_report`; they are re-exported
here so the module stays the one import path (`_read` below is the piece they
resolve `LOG_DIR` through, which keeps it monkeypatchable).

Usage:
  python -m tools.progress_from_log [YYYY-MM-DD]     # default: today (UTC)
"""

import os
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.progress_from_log_collect import collect, passes_gate  # noqa: E402,F401
from tools.progress_from_log_patterns import (  # noqa: E402,F401
    ALPHA_RE,
    BATCH_ALPHA_RE,
    CHECK_RE,
    CHECK_SUMMARY_RE,
    ERROR_BATCH_RE,
    FITNESS_FLOOR,
    POLISH_RE,
    SHARPE_FLOOR,
    SHARPE_FLOOR_DEFAULT,
    TEMPLATE_RE,
    TURNOVER_BAND,
)
from tools.progress_from_log_report import main, report  # noqa: E402,F401

LOG_DIR = os.environ.get("BRAIN_LOG_DIR", os.path.join(PROJECT_DIR, "brain_logs"))


def _read(name: str, day: str) -> list[str]:
    """Lines for `day` from `name` — the live file plus any rotated copy."""
    lines: list[str] = []
    for path in (os.path.join(LOG_DIR, f"{name}.{day}"), os.path.join(LOG_DIR, name)):
        if not os.path.exists(path):
            continue
        with open(path, errors="replace") as fh:
            for line in fh:
                if line.startswith(day):
                    lines.append(line.rstrip("\n"))
    return lines


if __name__ == "__main__":
    sys.exit(main())
