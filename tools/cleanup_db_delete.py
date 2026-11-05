"""The destructive phase of a cleanup run: delete, VACUUM, stamp.

Split out of `tools/cleanup_db.py`. The caller passes a connection it already
holds; nothing here reads a module-level path.
"""

import time
from datetime import UTC, datetime

from core.db import OperationalError
from core.scope import scope_sql
from tools.cleanup_db_rules import RULES, TARGET_RULES


def delete_all(conn, args) -> int:
    """Delete every out-of-scope row the flags cover; return the count."""
    deleted = 0
    print("\ndeleting ...")

    def delete_not(table, condition):
        """Delete the rows failing `condition`, returning how many went."""
        # DuckDB's rowcount is -1 for DELETE, so count with RETURNING.
        return len(conn.execute(f"DELETE FROM {table} WHERE NOT ({condition}) RETURNING 1").fetchall())

    for table, _column, keep in RULES:
        gone = delete_not(table, keep)
        deleted += gone
        print(f"  {table:20} -{gone:,}")
    if args.prune_targets:
        for table, column in TARGET_RULES:
            try:
                gone = delete_not(table, scope_sql(column))
                deleted += gone
                print(f"  {table:20} -{gone:,}")
            except OperationalError:
                pass
    if args.drop_blacklist:
        conn.execute("DROP TABLE IF EXISTS field_blacklist")
        print("  field_blacklist      dropped")
    conn.commit()
    print(f"  total deleted: {deleted:,}")
    return deleted


def vacuum(conn):
    print("\nvacuuming (rewrites the file, may take a while) ...")
    t0 = time.time()
    conn.execute("VACUUM")
    print(f"  done in {time.time() - t0:.1f}s")


def stamp_cleanup(conn):
    conn.execute(
        "INSERT OR REPLACE INTO metadata VALUES (?,?)",
        ("last_cleanup", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")),
    )
    conn.commit()
