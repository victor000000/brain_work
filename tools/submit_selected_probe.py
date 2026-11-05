"""Inspect one queued probe, or explicitly submit only that owner once.

No explorer startup, random generation or alpha submission. One dispatch uses
the ordinary quota-aware transport policy; it does not loop over queued work.
An accepted simulation remains durably receipted for subsequent reconciliation.
Submission requires an authorized allowance window; receipt polling may finish
after that window. Stop the explorer before either operation.
"""

import argparse
import fcntl
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.auth import get_session
from core.db import get_conn
from core.log import setup_logging
from core.log_config import LOG_DIR
from runner.explore_loop.reattach_scan import build_batches
from runner.poll_batch import poll_batch
from runner.probe_queue import submit_queued_probe


def reserve_selected_batch(conn, probe_id):
    """Reserve under the sole-writer lock before any potentially uncertain POST.

    Probe IDs remain authoritative. Legacy errors supply a migration floor;
    historical collisions are never rewritten or used to reconcile requests.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS selected_probe_attempts (batch_idx BIGINT PRIMARY KEY, probe_id VARCHAR NOT NULL)"
    )
    index = conn.execute(
        "SELECT COALESCE(MAX(idx), 0)+1 FROM ("
        "SELECT batch_idx AS idx FROM simulations UNION ALL "
        "SELECT batch_idx FROM selected_probe_attempts UNION ALL "
        "SELECT TRY_CAST(regexp_extract(error_message, '^B([0-9]+):', 1) AS BIGINT) "
        "FROM probe_batches)"
    ).fetchone()[0]
    conn.execute("INSERT INTO selected_probe_attempts VALUES (?, ?)", (index, probe_id))
    conn.commit()
    return index


def submit_selected(session, conn, probe_id):
    """One selected-owner dispatch; absence/ineligibility never falls through."""
    index = reserve_selected_batch(conn, probe_id)
    handled, result = submit_queued_probe(session, conn, index, probe_id=probe_id)
    return {"probe_id": probe_id, "handled": handled, "result": result}


def poll_selected(session, conn, probe_id):
    """One GET/store pass on an exact receipted owner, regardless of its age."""
    owner = conn.execute(
        "SELECT parent_id, expressions, settings FROM probe_batches WHERE probe_id=?", (probe_id,)
    ).fetchone()
    if not owner or not owner[0]:
        raise ValueError("Selected probe has no stored parent receipt; do not resubmit")
    row = conn.execute(
        "SELECT sim_id, batch_idx, region, universe, delay, expression, raw_settings, submitted_at, status "
        "FROM simulations WHERE sim_id=? AND parent_id IS NULL",
        (owner[0],),
    ).fetchone()
    if row is None:
        raise ValueError("Stored parent is missing; reconcile the receipt without resubmission")
    if json.loads(row[5]) != json.loads(owner[1]) or json.loads(row[6]) != json.loads(owner[2]):
        raise ValueError("Parent payload differs from selected owner")
    report = {"probe_id": probe_id, "parent_id": owner[0], "stored_status": row[8]}
    if row[8] != "SUBMITTED":
        return report
    batches = build_batches([row[:8]], time.time())
    if len(batches) != 1:
        raise ValueError("Cannot reconstruct selected parent")
    batch = batches[0]
    report["poll_complete"] = poll_batch(session, batch, conn)
    report["stored_status"] = conn.execute("SELECT status FROM simulations WHERE sim_id=?", (owner[0],)).fetchone()[0]
    report["next_poll_after_seconds"] = max(25, batch.get("retry_after") or 0)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-id", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="send only this queued probe if eligible")
    mode.add_argument("--poll", action="store_true", help="GET/store one pass for this owner's recorded parent")
    args = parser.parse_args()
    setup_logging(console_stream=sys.stderr)
    lock_path = Path(LOG_DIR) / "explorer.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        conn = get_conn()
        try:
            conn.execute("CHECKPOINT")
            row = conn.execute(
                "SELECT state, parent_id, expressions, settings FROM probe_batches WHERE probe_id=?",
                (args.probe_id,),
            ).fetchone()
            if row is None:
                parser.error("Unknown probe owner; queue a validated plan first")
            report = {"probe_id": args.probe_id, "state": row[0], "parent_id": row[1]}
            if args.execute:
                report["dispatch"] = submit_selected(get_session(raise_on_failure=True), conn, args.probe_id)
            elif args.poll:
                report["poll"] = poll_selected(get_session(raise_on_failure=True), conn, args.probe_id)
            else:
                report.update(expressions=json.loads(row[2]), settings=json.loads(row[3]))
            print(json.dumps(report, indent=2))
        finally:
            conn.close()


if __name__ == "__main__":
    main()
