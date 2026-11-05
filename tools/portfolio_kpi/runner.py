"""Top-level runner for `python3 -m tools.portfolio_kpi`."""

import sys
import time

from core.db import get_conn
from tools.portfolio_kpi.accumulate import accumulate_population
from tools.portfolio_kpi.populations import POPULATIONS
from tools.portfolio_kpi.render import format_block


def _load_p_max(conn) -> int:
    """Distinct pyramid categories from pyramid_multipliers (latest snapshot is fine —
    the category set is stable across snapshots, only multipliers and counts change).
    """
    return conn.execute("SELECT COUNT(DISTINCT category) FROM pyramid_multipliers").fetchone()[0]


def main() -> int:
    # Read-only report: no DDL/migrations here — creating tables from a report
    # can mask a missing database or race a migration.
    conn = get_conn()

    p_max = _load_p_max(conn)
    if p_max == 0:
        print(
            "ERROR: pyramid_multipliers table is empty — run `python3 -m tools.refresh_pyramid_state` first.",
            file=sys.stderr,
        )
        return 1

    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    print(f"Portfolio Shape KPI -- {now_str}")
    print(f"P_max = {p_max} distinct pyramid categories\n")

    for label, where in POPULATIONS:
        stats = accumulate_population(conn, where)
        print(format_block(label, stats, p_max))

    return 0
