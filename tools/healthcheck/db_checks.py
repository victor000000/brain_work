"""Checks on what the pv/option database holds and how it is structured.

Split out of `tools/healthcheck/checks.py`, which re-exports these names.
"""

from core.scope import scope_sql
from tools.healthcheck.check_base import _count, check


def check_integrity(conn):
    """Every table must be readable end to end.

    DuckDB has no `PRAGMA integrity_check`; it validates block checksums as it
    reads, so scanning each table (a real scan, via a distinct aggregate) is
    the equivalent exercise. A corrupt file raises here.
    """
    print("[Integrity]")
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='main' AND table_type='BASE TABLE'"
            )
        ]
        for table in tables:
            # SUM over every column forces DuckDB to read every block; a
            # metadata-only COUNT(*) would not.
            columns = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
            if not columns:
                continue
            total_len = " + ".join(f'COALESCE(LENGTH(CAST("{c}" AS VARCHAR)), 0)' for c in columns)
            conn.execute(f'SELECT SUM({total_len}) FROM "{table}"').fetchone()
    except Exception as err:  # a corrupt file can raise rather than report
        return check("DuckDB readability", False, str(err))
    return check("DuckDB readability", True, f"{len(tables)} tables scanned")


def check_scope(conn):
    """No non-pv/option category may appear in the scope-bound tables.

    `store_categories` once re-inserted all 62 categories after the cleanup.
    The guard is structural now, but these tables must also be clean.
    """
    print("[Scope]")
    ok = True
    checks = (
        ("data_fields", "category_id"),
        ("datasets", "category_id"),
        ("dataset_categories", "id"),
    )
    for table, column in checks:
        try:
            # `NOT (col IN (...) ...)` is NULL for a NULL category, so a row
            # with no category at all was counted as in scope — while
            # `in_scope(None)` is False and the write guard rejects it. Such a
            # row is corrupt, so surface it too.
            bad = _count(conn, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL OR NOT {scope_sql(column)}")
        except Exception as err:
            ok &= check(f"{table} in scope", False, f"query failed: {err}")
            continue
        ok &= check(f"{table} in scope", bad == 0, f"{bad} out-of-scope rows")
    return ok


def check_results(conn):
    """Check alpha results are accumulating and attributed to templates."""
    print("\n[Results]")
    total = _count(conn, "SELECT COUNT(*) FROM alpha_results")
    ok = check("Alpha results", total > 0, f"{total:,} alphas")
    if total == 0:
        return ok
    pos = _count(conn, "SELECT COUNT(*) FROM alpha_results WHERE is_sharpe > 0")
    ok &= check("Positive alphas", pos > 0, f"{pos:,} positive ({pos * 100 // max(total, 1)}%)")

    # Only alphas carrying a template can be tracked at all; comparing the
    # tracking table to every alpha row (including pre-attribution ones) made
    # this fail for reasons that were not actionable.
    templated = _count(conn, "SELECT COUNT(*) FROM alpha_results WHERE template IS NOT NULL AND template != ''")
    tracked = _count(conn, "SELECT COUNT(*) FROM template_performance")
    enough = tracked >= templated * 0.9 if templated else tracked > 0
    ok &= check("Template tracking", enough, f"{tracked:,}/{templated:,} templated alphas")
    return ok
