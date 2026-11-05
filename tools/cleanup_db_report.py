"""The read-only reporting phase of a cleanup run.

Split out of `tools/cleanup_db.py`. Each function prints exactly the block it
printed inline before the split, in the same order.
"""

from core.db import OperationalError
from core.scope import scope_sql
from tools.cleanup_db_rules import RULES, TARGET_RULES


def counts(conn):
    out = {}
    for table, column, keep in RULES:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        kept = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {keep}").fetchone()[0]
        out[table] = (total, kept, total - kept, column)
    return out


def print_scope(scope):
    print("\n=== rows to delete ===")
    for table, (total, kept, gone, _column) in scope.items():
        print(f"  {table:20} {total:>9,} total  {kept:>9,} kept  {gone:>9,} deleted")


def print_targets(conn):
    print("\n=== pyramid rows (--prune-targets) ===")
    for table, column in TARGET_RULES:
        try:
            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            kept = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {scope_sql(column)}").fetchone()[0]
            print(f"  {table:20} {total:>9,} total  {kept:>9,} kept  {total - kept:>9,} deleted")
        except OperationalError as err:
            print(f"  {table:20} skipped ({err})")


def print_blacklist(conn):
    if conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema='main' AND table_name='field_blacklist'"
    ).fetchone():
        n = conn.execute("SELECT COUNT(*) FROM field_blacklist").fetchone()[0]
        print(f"\n  field_blacklist      {n:>9,} rows — table will be dropped")
    else:
        print("\n  field_blacklist      already absent — nothing to drop")
