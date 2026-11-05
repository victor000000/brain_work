#!/usr/bin/env python3
"""Validate a finite probe plan; --apply queues it for the normal explorer.

Use --request while the explorer runs; its writer validates and queues the plan.
Stop the supervisor before direct validation or --apply against live DuckDB.
Do not create database backups. No API requests are made.
Each batch needs expressions, settings and one template_tags entry per expression.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_DIR = str(Path(__file__).resolve().parents[1])
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from core.db import DB_PATH, connect, connect_for_reading, init_tables  # noqa: E402
from runner.probe_queue_store import enqueue_probe  # noqa: E402
from runner.probe_requests import request_probe_plan  # noqa: E402
from runner.probe_validation import validate_probe  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--db", default=DB_PATH)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--request", action="store_true", help="publish a request without opening DuckDB")
    args = parser.parse_args()
    if args.request:
        if args.db != DB_PATH:
            parser.error("--request is handled by the live writer and cannot target --db")
        print(json.dumps(request_probe_plan(args.plan), indent=2))
        return 0
    document = json.loads(Path(args.plan).read_text())
    batches = document["batches"]
    if not isinstance(batches, list) or not batches:
        parser.error("plan must contain at least one batch")
    conn = connect(args.db) if args.apply else connect_for_reading(args.db)
    try:
        for batch in batches:
            validate_probe(conn, batch["expressions"], batch["settings"], batch["template_tags"])
        result = {
            "batches": len(batches),
            "expressions": sum(len(batch["expressions"]) for batch in batches),
            "applied": args.apply,
        }
        if args.apply:
            init_tables(conn)
            result["queue"] = [
                dict(
                    zip(
                        ("probe_id", "inserted"),
                        enqueue_probe(conn, batch["expressions"], batch["settings"], batch["template_tags"]),
                        strict=True,
                    )
                )
                for batch in batches
            ]
        print(json.dumps(result, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
