"""Store the parent simulation row for a batch BRAIN accepted (HTTP 201).

Split out of `runner/submit_batch.py`, which re-exports `store_accepted_batch`.
Assembling and posting the payload is retry/pacing work; everything after the
201 is this: turning a Location header into a tracked parent row, because a
lost batch burns quota and leaks a concurrent slot.
"""

import json
import logging
import time

from core.budget import BUDGET_FLOOR
from core.log import get_file_logger
from runner.submit_batch_log import log_batch_success
from storage.store_sim import store_sim

API_BASE = "https://api.worldquantbrain.com"
log = logging.getLogger("brain")
slog = get_file_logger("submit")


def store_accepted_batch(conn, resp, expressions, settings, batch_idx, remaining):
    """Store an accepted batch's parent row. Returns its info dict, or None.

    A 201 means BRAIN accepted the batch and it is now running. From here on
    it MUST be stored so the poll loop can find it — losing it burns quota and
    leaks a concurrent slot.
    """
    # Parse location to get parent simulation ID
    location = resp.headers.get("Location", "")
    if not location:
        slog.error(
            "B%d: HTTP 201 without Location header — accepted batch cannot be tracked, abandoning",
            batch_idx,
        )
        log.error("B%d: accepted batch has no Location header", batch_idx)
        return None
    if location.startswith("/"):
        location = API_BASE + location
    parent_id = location.rstrip("/").split("/")[-1]
    if not parent_id:
        slog.error("B%d: malformed Location header %r — abandoning batch", batch_idx, location)
        log.error("B%d: malformed Location header", batch_idx)
        return None

    # Store parent simulation record. Expressions are kept on the parent row
    # (as JSON) so a crash/restart can re-attach the batch and still attribute
    # child results correctly.
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    store_sim(
        conn,
        parent_id,
        None,
        batch_idx,
        json.dumps(expressions),
        settings["region"],
        settings["universe"],
        settings["delay"],
        "SUBMITTED",
        None,
        None,
        settings,
        now,
        # The batch was accepted at `now`; the parent's submitted_at is this
        # instant, and the children written by the poll loop carry the same
        # value (from the batch's `submitted_at`), so a child's latency is
        # `completed_at - submitted_at`.
        submitted_at=now,
    )

    # Log success
    reset_sec = resp.headers.get("X-Ratelimit-Reset", "?")
    log_batch_success(batch_idx, settings, expressions, remaining, reset_sec)

    slog.debug(
        "B%d: parent=%s loc=%s region=%s/%s",
        batch_idx,
        parent_id,
        location,
        settings["region"],
        settings["universe"],
    )

    # An absent header is "unknown", not "exhausted": keep submitting unless the
    # remaining count is actually known to be at/under the floor.
    budget_low = remaining is not None and remaining < BUDGET_FLOOR
    if budget_low:
        slog.warning(
            "B%d: low budget (%s remaining) — pausing new submits, batch stays in flight", batch_idx, remaining
        )

    return {
        "pid": parent_id,
        "loc": location,
        "exprs": expressions,
        "idx": batch_idx,
        "settings": settings,
        "budget_remaining": remaining,
        "budget_low": budget_low,
        "submitted_at": time.time(),
    }
