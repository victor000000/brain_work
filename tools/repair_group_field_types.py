#!/usr/bin/env python3
"""Correct `data_fields.type` for fields BRAIN reports as GROUP but we store MATRIX.

A field the platform types GROUP that sits in our matrix pool reaches operators
that take a matrix, and the simulation comes back
`Incompatible unit ... found "Unit[Group:1]"` — a budget slot spent for nothing.
Observed 2026-10-06 on `technology_pca_factor2_grouping5` (`ts_arg_max`, USA/
TOP500/d1) and again on a sibling (`ts_delta`, USA/TOP200/d0).

`query_matrix_fields` filters on this column, so one UPDATE both drops the field
from the matrix pool and lets `query_group_fields` offer it as a group.

Input is the id map built by the offline fetch (`type='GROUP'` per subcategory,
because a whole-universe query hits the API's offset cap):

    {"<REGION>/<UNIVERSE>/d<DELAY>": [id, ...], ...}

The fetch is read-only and free, so it runs while the explorer works; only this
UPDATE needs the write lock. Run it in the budget-exhausted window, when the
explorer is idling and a stop costs no simulations:

    make stop
    python3 tools/repair_group_field_types.py /tmp/group_fields.json --dry-run
    python3 tools/repair_group_field_types.py /tmp/group_fields.json
    make start

A cell absent from the map is skipped, never treated as "nothing is a group":
an under-fetched list would silently repair nothing.
"""

import argparse
import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.db import connect

DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")


def _parse_cell(key):
    """'USA/TOP500/d1' -> ('USA', 'TOP500', 1), or None when malformed."""
    try:
        region, universe, delay = key.split("/")
        return region, universe, int(delay.lstrip("d"))
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map_path", help="JSON of {cell: [group field id, ...]}")
    ap.add_argument("--dry-run", action="store_true", help="report, change nothing")
    args = ap.parse_args()

    with open(args.map_path) as fh:
        mapping = json.load(fh)

    conn = connect(DB_PATH)
    total = 0
    try:
        for key, ids in sorted(mapping.items()):
            cell = _parse_cell(key)
            if cell is None or not ids:
                print(f"  {key:24} skipped (malformed or empty)")
                continue
            region, universe, delay = cell
            placeholders = ",".join("?" * len(ids))
            sql = (
                "SELECT COUNT(*) FROM data_fields "
                f"WHERE region=? AND universe=? AND delay=? AND type='MATRIX' AND id IN ({placeholders})"
            )
            params = [region, universe, delay, *ids]
            n = conn.execute(sql, params).fetchone()[0]
            print(f"  {key:24} {n:4} of {len(ids):4} GROUP ids stored as MATRIX")
            total += n
            if n and not args.dry_run:
                conn.execute(
                    "UPDATE data_fields SET type='GROUP' "
                    f"WHERE region=? AND universe=? AND delay=? AND type='MATRIX' AND id IN ({placeholders})",
                    params,
                )
                conn.commit()
        print(f"\n{'would correct' if args.dry_run else 'corrected'} {total} rows")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
