"""Store simulation records and error tracking.

The `sim_errors` sidecar lives in `storage.store_sim_errors` and the poll-loop
status updates in `storage.store_sim_status`; both are re-exported here so
`from storage.store_sim import ...` keeps resolving for every caller.
"""

import json
import logging
import time

from core.log import get_file_logger
from storage.store_sim_errors import _ensure_sim_errors_schema, _record_error  # noqa: F401
from storage.store_sim_status import _KEEP_ERROR, update_sim_status  # noqa: F401

log = logging.getLogger("brain")
elog = get_file_logger("errors")


def utc_text(epoch) -> str | None:
    """Epoch seconds as the project's `YYYY-MM-DD HH:MM:SS UTC` text, or None."""
    return None if epoch is None else time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(epoch))


def store_sim(
    conn,
    sim_id,
    parent_id,
    batch_idx,
    expr,
    region,
    universe,
    delay,
    status,
    alpha_id,
    error_msg,
    settings,
    completed_at,
    submitted_at=None,
):
    """Store a simulation record (parent or child).

    `submitted_at` is the batch's submission time, in the same text form as
    every other timestamp here. The column has been in the schema from the
    start and was written by nothing: all 322,047 rows read NULL at 2026-10-12,
    so no per-simulation latency could be measured from the database — "is this
    shape slow?" had to be argued from the poll logs, which report per-batch
    progress rather than per-child duration. Callers that know when the batch
    went out now pass it; rows written without one keep the NULL.
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO simulations
        (sim_id, parent_id, batch_idx, expression, region, universe,
         delay, status, alpha_id, error_message, submitted_at, completed_at, raw_settings)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """,
        (
            sim_id,
            parent_id,
            batch_idx,
            expr,
            region,
            universe,
            delay,
            status,
            alpha_id,
            error_msg,
            submitted_at,
            completed_at,
            json.dumps(settings),
        ),
    )

    # Record and log errors
    if expr and error_msg and status in ("ERROR", "FAIL"):
        _record_error(conn, expr, region, error_msg, settings, completed_at, sim_id=sim_id)
        elog.warning("SIM %s %s/%s: %s — %s", sim_id, region, universe, status, error_msg[:80])
        log.debug("Sim error %s: %s — %s", sim_id, status, error_msg[:60])

    if status == "CANCELLED":
        elog.debug("SIM %s CANCELLED (%s/%s)", sim_id, region, universe)

    conn.commit()
