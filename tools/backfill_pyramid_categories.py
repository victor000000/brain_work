#!/usr/bin/env python3
"""Backfill alpha_results.pyramid_categories for rows where it IS NULL.

Reads data_fields.category_id (97K rows), then iterates over alpha_results
deriving the category set from each expression. No API calls.

Usage: python3 -m tools.backfill_pyramid_categories
"""

from core.db import get_conn, init_tables
from storage.track_pyramid import derive_pyramid_categories, load_field_to_category


def main():
    conn = get_conn()
    init_tables(conn)
    field_to_category = load_field_to_category(conn)
    print(f"Loaded {len(field_to_category)} fields with category_id.")

    rows = conn.execute(
        "SELECT alpha_id, expression FROM alpha_results WHERE pyramid_categories IS NULL AND expression IS NOT NULL"
    ).fetchall()
    print(f"Backfilling {len(rows)} rows...")

    updates = [(derive_pyramid_categories(expr, field_to_category), aid) for aid, expr in rows]
    with conn:
        conn.executemany(
            "UPDATE alpha_results SET pyramid_categories = ? WHERE alpha_id = ?",
            updates,
        )

    # Summary by category-set size.
    print("\nDistribution by category-set size:")
    size_rows = conn.execute(
        """
        SELECT json_array_length(pyramid_categories) AS n, COUNT(*)
        FROM alpha_results
        WHERE pyramid_categories IS NOT NULL
        GROUP BY n
        ORDER BY n
        """
    ).fetchall()
    for n, c in size_rows:
        print(f"  {n} categor{'y' if n == 1 else 'ies'}: {c} alphas")

    nulls = conn.execute("SELECT COUNT(*) FROM alpha_results WHERE pyramid_categories IS NULL").fetchone()[0]
    print(f"  NULL: {nulls} alphas (no recognizable fields)")

    # Top 10 categories among single-category alphas — sanity-check signal.
    print("\nTop 10 categories among single-category alphas:")
    top_rows = conn.execute(
        """
        SELECT json_extract_string(pyramid_categories, '$[0]') AS cat, COUNT(*) AS n
        FROM alpha_results
        WHERE json_array_length(pyramid_categories) = 1
        GROUP BY cat
        ORDER BY n DESC
        LIMIT 10
        """
    ).fetchall()
    for cat, n in top_rows:
        print(f"  {n:>5} {cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
