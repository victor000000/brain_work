#!/usr/bin/env python3
"""Refresh pyramid_multipliers + pyramid_alpha_counts from BRAIN. Manual one-shot.

Usage: python3 -m tools.refresh_pyramid_state
"""

import time

from core.auth import get_session
from core.db import get_conn, init_tables
from download.pyramid import (
    fetch_pyramid_state,
    get_current_pyramid_state,
    store_pyramid_state,
)


def main():
    session = get_session()
    conn = get_conn()
    init_tables(conn)

    multipliers, alpha_counts = fetch_pyramid_state(session)
    if multipliers is None or alpha_counts is None:
        print("Fetch failed — see logs for details.")
        return 1

    fetched_at = int(time.time())
    store_pyramid_state(conn, multipliers, alpha_counts, fetched_at=fetched_at)
    print(f"Wrote {len(multipliers)} multiplier rows + {len(alpha_counts)} alpha-count rows at t={fetched_at}.")

    state = get_current_pyramid_state(conn)
    top10 = state[:10]
    print("\nTop 10 cells (highest multiplier, lowest alpha_count tiebreak):")
    print(f"  {'mult':>5} {'count':>5}  {'category':>16}  {'region':>3} {'d':>1}")
    for row in top10:
        print(
            f"  {row['multiplier']:>5.2f} {row['alpha_count']:>5}  "
            f"{row['category']:>16}  {row['region']:>3} {row['delay']:>1}"
        )

    zero_count_in_top_decile = sum(1 for r in state[: max(len(state) // 10, 1)] if r["alpha_count"] == 0)
    print(
        f"\nUndersaturated (alpha_count==0) cells in top decile: "
        f"{zero_count_in_top_decile} / {max(len(state) // 10, 1)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
