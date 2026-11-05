#!/usr/bin/env python3
"""Prune brain_data.duckdb to price (pv) and options (option) data only.

Removes every field, dataset and category that the generator can no longer
reach, then VACUUMs to reclaim the space.

Destructive and irreversible. Always run --dry-run first, and --backup is
strongly recommended (a 1.4 GB copy is cheap against ~950 GB free). Do not run
while another process is writing the DB (e.g. the pv/option field refresh) —
VACUUM needs exclusive access and will fail or block.

The phases live in `cleanup_db_report`, `cleanup_db_delete` and
`cleanup_db_run`; `backup_database`/`active_writer` stay here because they are
the pieces that must read this module's `DB_PATH` (tests monkeypatch it).

Usage:
    python3 tools/cleanup_db.py --dry-run
    python3 tools/cleanup_db.py --backup --execute
    python3 tools/cleanup_db.py --backup --execute --drop-blacklist
"""

import os
import shutil
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.db import OperationalError, connect  # noqa: E402
from tools.cleanup_db_rules import RULES, TARGET_RULES  # noqa: E402,F401
from tools.cleanup_db_run import parse_args, run  # noqa: E402

DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")


def active_writer():
    """True when another process holds the database.

    DuckDB allows several connections per process but only one process per
    file, so opening the file here fails exactly when someone else (the
    explorer) has it. A connection this process already holds does not count.
    """
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = connect(DB_PATH)
    except OperationalError:
        return True
    conn.close()
    return False


def backup_database(backup_path):
    """Copy the live DB after a CHECKPOINT.

    DuckDB allows one process per file, so whoever holds the connection has
    the database to themselves; folding the write-ahead log in with CHECKPOINT
    and then copying the file yields a consistent snapshot. There is no
    override for a busy database — the holder simply has to stop, because a
    torn or stale copy is worse than no copy at all.
    """
    try:
        conn = connect(DB_PATH)
    except OperationalError:
        print("error: another process holds the database; stop it before backing up")
        return False

    try:
        conn.execute("CHECKPOINT")
        wal = DB_PATH + ".wal"
        if os.path.exists(wal) and os.path.getsize(wal) > 0:
            print("note: non-empty .wal after CHECKPOINT; the backup may lag commits")
        shutil.copy2(DB_PATH, backup_path)
    finally:
        conn.close()
    return True


def main():
    ap, args = parse_args()
    if not (args.dry_run or args.execute):
        ap.print_help()
        return

    if not os.path.exists(DB_PATH):
        print(f"no database at {DB_PATH}")
        sys.exit(1)

    run(args, DB_PATH, backup_database)


if __name__ == "__main__":
    main()
