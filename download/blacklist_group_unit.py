"""Empirical blacklist for MATRIX-typed fields with Unit[Group:1] semantics.

Some BRAIN fields are stored as type='MATRIX' but are semantically group/cluster
identifiers (descriptions like "Industry grouping using method 1 with 5 clusters").
Passing them to rank/add/ts_zscore/ts_regression produces Unit[Group:1] errors
that waste daily simulation budget.

This module scans `simulations` for past Unit[Group:1] errors, extracts field
tokens from the failing expressions, intersects with known MATRIX field IDs,
and writes the result to `field_blacklist` with reason='group_unit'. The
existing `query_matrix_fields` (in generator/field_queries_matrix.py) already
filters via the blacklist, so the runtime path is unchanged.

Conservative collateral inclusion: every MATRIX field appearing in a failing
expression is blacklisted, even if it wasn't strictly the cause. Cost is
bounded — the same fields would be tried again on the next backfill if their
failure was incidental and they keep appearing only in successful sims
elsewhere. (Today the design re-blacklists rather than un-blacklists, so
collateral is slightly sticky. Acceptable until proven otherwise.)

This module remains the CLI entry point (`python -m download.blacklist_group_unit`).
The scan lives in `download.blacklist_group_unit_scan` and the write in
`download.blacklist_group_unit_store`; both are re-exported here so every
existing `from download.blacklist_group_unit import ...` keeps resolving.
"""

from __future__ import annotations

from download.blacklist_group_unit_scan import (  # noqa: F401
    extract_field_tokens,
    find_group_unit_offenders,
)
from download.blacklist_group_unit_store import backfill_blacklist


def main() -> int:
    """CLI entrypoint: backfill field_blacklist from past sim errors.

    The blacklist was removed deliberately on 2026-10-02 — generation is
    category-filtered (pv/option only) and blocks no individual field — so the
    table no longer exists. Report that instead of raising OperationalError.
    `find_group_unit_offenders(conn)` still works standalone as a diagnostic:
    it reads `simulations`, not the blacklist.
    """
    from core.db import get_conn

    conn = get_conn()
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='main' AND table_type='BASE TABLE'"
        )
    }
    if "field_blacklist" not in tables:
        conn.close()
        print("field_blacklist no longer exists — nothing to update.")
        print()
        print("The blacklist was removed deliberately; the field pool is now")
        print("category-filtered to pv/option with no per-field blocking.")
        print("find_group_unit_offenders(conn) remains available as a diagnostic")
        print("for fields implicated in Unit[Group:1] simulation errors.")
        return 1

    before_total = conn.execute("SELECT COUNT(*) FROM field_blacklist").fetchone()[0]
    inserted = backfill_blacklist(conn)
    after_group = conn.execute("SELECT COUNT(*) FROM field_blacklist WHERE reason = 'group_unit'").fetchone()[0]
    by_region = conn.execute(
        "SELECT region, COUNT(*) FROM field_blacklist WHERE reason = 'group_unit' GROUP BY region ORDER BY 2 DESC"
    ).fetchall()
    conn.close()

    print(f"Inserted: {inserted} new rows")
    print(f"Total group_unit rows: {after_group}")
    print(f"Total blacklist rows (all reasons): {before_total + inserted}")
    print("By region:")
    for region, count in by_region:
        print(f"  {region}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
