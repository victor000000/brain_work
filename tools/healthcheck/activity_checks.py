"""Checks that the explorer is running *and* producing recent results.

Split out of `tools/healthcheck/checks.py`, which re-exports these names.
"""

import subprocess
import time

from tools.healthcheck.check_base import _parse_iso, check
from tools.healthcheck.thresholds import ALPHA_RESULTS_MAX_AGE_DAYS, EXPLORER_PROGRESS_MAX_AGE_HOURS


def check_alpha_recency(conn):
    """alpha_results must contain recent rows — a stuck explorer writes none."""
    print("\n[Activity]")
    raw = conn.execute("SELECT MAX(created_at) FROM alpha_results").fetchone()[0]
    ts = _parse_iso(raw)
    if ts is None:
        return check("Alpha results recent", False, f"no parseable created_at (got {raw!r})")
    age_days = (time.time() - ts) / 86400
    return check(
        "Alpha results recent",
        age_days <= ALPHA_RESULTS_MAX_AGE_DAYS,
        f"newest {raw} ({age_days:.1f} days ago, limit {ALPHA_RESULTS_MAX_AGE_DAYS})",
    )


def check_explorer_progress(conn):
    """The explorer must be *progressing*, not merely running.

    A live process that has produced nothing for a day is stuck (auth loop,
    exhausted budget, crashed children) and the process check alone cannot see
    that.
    """
    newest = conn.execute("SELECT MAX(created_at) FROM alpha_results").fetchone()[0]
    ts = _parse_iso(newest)
    if ts is None:
        return check("Explorer progressing", False, f"no parseable alpha timestamp (got {newest!r})")
    age_hours = (time.time() - ts) / 3600
    return check(
        "Explorer progressing",
        age_hours <= EXPLORER_PROGRESS_MAX_AGE_HOURS,
        f"newest alpha {age_hours:.1f}h ago (limit {EXPLORER_PROGRESS_MAX_AGE_HOURS}h)",
    )


def check_processes():
    """Check explorer processes are running."""
    print("\n[Processes]")
    ps = subprocess.run(["pgrep", "-f", "simulate_alphas"], capture_output=True, text=True)
    procs = len(ps.stdout.strip().split("\n")) if ps.stdout.strip() else 0
    return check("Explorer process running", procs >= 1, f"{procs} processes")
