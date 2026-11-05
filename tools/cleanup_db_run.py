"""The cleanup phases, in the order the CLI runs them.

Split out of `tools/cleanup_db.py`. The database path and the backup callable
are parameters, so the module never reads a path global of its own — the
caller's `DB_PATH` (which tests monkeypatch) is what is acted on.
"""

import argparse
import os
import sys
import time
from datetime import UTC, datetime

from core.db import connect
from tools.cleanup_db_delete import delete_all, stamp_cleanup, vacuum
from tools.cleanup_db_report import counts, print_blacklist, print_scope, print_targets


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report scope, delete nothing (wins over --execute)")
    ap.add_argument("--execute", action="store_true", help="perform the deletion")
    ap.add_argument("--backup", action="store_true", help="copy the DB before touching it")
    ap.add_argument("--vacuum", action="store_true", default=True, help="reclaim space after")
    ap.add_argument("--no-vacuum", dest="vacuum", action="store_false")
    ap.add_argument("--prune-targets", action="store_true", help="also drop non-pv/option pyramid rows")
    ap.add_argument("--drop-blacklist", action="store_true", help="drop the unused field_blacklist table")
    return ap, ap.parse_args()


def run(args, db_path, backup):
    """Report scope, then (unless --dry-run) back up, delete, vacuum and stamp."""
    size_before = os.path.getsize(db_path)
    print(f"database: {db_path}")
    print(f"size    : {size_before / 1e9:.2f} GB")

    conn = connect(db_path)
    print_scope(counts(conn))
    if args.prune_targets:
        print_targets(conn)
    if args.drop_blacklist:
        print_blacklist(conn)
    conn.close()

    if args.dry_run:
        # Destructive and irreversible: when both flags are given the safe one
        # wins — same convention as tools/refresh_pyramid_targets.
        print("\ndry run — nothing deleted")
        return

    if args.backup:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = f"{db_path}.bak-{stamp}"
        print(f"\nbacking up to {backup_path} (CHECKPOINT + copy) ...")
        t0 = time.time()
        if not backup(backup_path):
            sys.exit(1)
        print(f"  done in {time.time() - t0:.1f}s ({os.path.getsize(backup_path) / 1e9:.2f} GB)")

    conn = connect(db_path)
    delete_all(conn, args)
    if args.vacuum:
        vacuum(conn)
    stamp_cleanup(conn)
    conn.close()

    size_after = os.path.getsize(db_path)
    print(
        f"\nsize: {size_before / 1e9:.2f} GB -> {size_after / 1e9:.2f} GB "
        f"(freed {(size_before - size_after) / 1e9:.2f} GB)"
    )
