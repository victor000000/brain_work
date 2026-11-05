#!/usr/bin/env python3
"""Backfill alpha_results.template for rows where template IS NULL.

Strategy (cheapest first):
  1. Copy template_performance.template_name (already populated by every
     past store_alpha call).
  2. For any orphans where template_performance has no row, fall back to
     storage.track_templates.identify_template (regex pattern matching).

Usage: python3 -m tools.backfill_template_column
"""

from core.db import get_conn, init_tables
from storage.track_templates import identify_template


def main():
    conn = get_conn()
    init_tables(conn)

    # Step 1: bulk-copy from template_performance where it exists.
    print("Step 1: copying from template_performance...")
    conn.execute(
        """
        UPDATE alpha_results
        SET template = (
            SELECT template_name FROM template_performance
            WHERE template_performance.alpha_id = alpha_results.alpha_id
        )
        WHERE template IS NULL
          AND alpha_id IN (SELECT alpha_id FROM template_performance)
        """
    )
    conn.commit()
    copied = conn.execute("SELECT COUNT(*) FROM alpha_results WHERE template IS NOT NULL").fetchone()[0]
    print(f"  template populated: {copied} rows")

    # Step 2: identify_template for remaining orphans.
    orphans = conn.execute(
        "SELECT alpha_id, expression FROM alpha_results WHERE template IS NULL AND expression IS NOT NULL"
    ).fetchall()
    print(f"Step 2: identifying {len(orphans)} orphans via regex fallback...")
    updates = []
    for alpha_id, expr in orphans:
        name = identify_template(expr)
        # identify_template returns 'unknown' when nothing matches; keep it
        # rather than NULL so refresh_priors includes the row in its grouping
        # (the 'unknown' bucket is its own cell — informative, not a black hole).
        updates.append((name, alpha_id))
    if updates:
        with conn:
            conn.executemany(
                "UPDATE alpha_results SET template = ? WHERE alpha_id = ?",
                updates,
            )
    print(f"  identify_template assigned: {len(updates)} rows")

    # Final summary.
    final_null = conn.execute("SELECT COUNT(*) FROM alpha_results WHERE template IS NULL").fetchone()[0]
    final_total = conn.execute("SELECT COUNT(*) FROM alpha_results").fetchone()[0]
    print(
        f"\nFinal: {final_total - final_null} / {final_total} rows have template; "
        f"{final_null} remain NULL (rows without expression text)."
    )
    print("\nTop 10 templates by count:")
    for name, n in conn.execute(
        "SELECT template, COUNT(*) FROM alpha_results "
        "WHERE template IS NOT NULL "
        "GROUP BY template ORDER BY 2 DESC LIMIT 10"
    ):
        print(f"  {name:>30}  {n:>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
