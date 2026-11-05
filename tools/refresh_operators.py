#!/usr/bin/env python3
"""Refresh the `operators` table from the platform's own list.

Why this exists: `generator/validate.py` builds its operator allowlist from
this table, so **an operator the platform has and this table does not is one
the generator can never emit** — any expression calling it is dropped as an
invented operator, and a mined skeleton that uses it fails `is_usable` at pool
load time. Nothing in the tree fetched `/operators`, so the table could only
rot: every operator the platform adds after the original import is invisible to
generation, to the pool filter and to the operator-coverage weighting.

Found 2026-10-11: the table held 83 operators and the platform returned 84. The
missing one was `vector_neut`.

Measured so the gap is not read as bigger than it is: adding `vector_neut` to
the allowlist unlocks **0** additional skeletons in the current mined pool
(569 usable either way) — the corpus rows that mention it are prose, or
reference fields outside the pv/option scope. The defect is the missing refresh
path, not that one operator.

Read-only against the platform; writes only the `operators` table. The explorer
holds the DuckDB file, so run this while it is stopped (or on the same
connection from inside a tool that already holds it).

Usage:
    python3 tools/refresh_operators.py [--dry-run]
"""

import argparse
import json
import os
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.auth import get_session  # noqa: E402
from core.db import DB_PATH, connect  # noqa: E402

API_BASE = "https://api.worldquantbrain.com"

DDL = """
CREATE TABLE IF NOT EXISTS operators (
    "name" VARCHAR, category VARCHAR, "level" VARCHAR, definition VARCHAR,
    description VARCHAR, "scope" VARCHAR, raw_json VARCHAR, PRIMARY KEY("name")
)
"""

INSERT = """
INSERT OR REPLACE INTO operators (name, category, level, definition, description, scope, raw_json)
VALUES (?,?,?,?,?,?,?)
"""


def fetch_operators(session):
    """The platform's operator list, as rows ready for the table."""
    resp = session.get(f"{API_BASE}/operators", timeout=60)
    resp.raise_for_status()
    rows = []
    for op in resp.json():
        name = op.get("name")
        if not name:
            continue
        rows.append(
            (
                name,
                op.get("category"),
                op.get("level"),
                op.get("definition"),
                op.get("description"),
                json.dumps(op.get("scope"), ensure_ascii=False) if op.get("scope") is not None else None,
                json.dumps(op, ensure_ascii=False),
            )
        )
    return rows


def main(conn=None, session=None):
    """Refresh the table, returning a process exit code.

    `conn` and `session` are injectable so a test — or a caller that already
    holds the database, which is the case whenever the explorer is running —
    does not have to open its own. Only what this function opened is closed.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report the diff, write nothing")
    args = parser.parse_args()

    session = session or get_session()
    fetched = fetch_operators(session)
    print(f"platform returned {len(fetched)} operators")

    owns_conn = conn is None
    conn = conn or connect(DB_PATH)
    try:
        conn.execute(DDL)
        have = {row[0] for row in conn.execute("SELECT name FROM operators").fetchall()}
        names = {row[0] for row in fetched}
        added, gone = sorted(names - have), sorted(have - names)
        print(f"table held {len(have)}; adding {len(added)}, removing {len(gone)}")
        for name in added:
            print(f"  + {name}")
        for name in gone:
            print(f"  - {name}  (the platform no longer lists it)")
        if args.dry_run:
            print("dry run: nothing written")
            return 0
        conn.executemany(INSERT, fetched)
        # An operator the platform dropped is not a syntax error to keep, but the
        # allowlist would let the generator emit a call the platform rejects —
        # exactly the one-simulation-per-expression waste this table exists to
        # prevent. Deleting is the point of a refresh, not a side effect.
        if gone:
            conn.executemany("DELETE FROM operators WHERE name = ?", [(n,) for n in gone])
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM operators").fetchone()[0]
        print(f"wrote {len(fetched)} rows; table now holds {total}")
    finally:
        if owns_conn:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
