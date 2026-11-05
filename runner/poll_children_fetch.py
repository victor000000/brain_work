"""Fetch and store a single child simulation result."""

import time

from core.log import get_file_logger
from runner.poll_alpha_fetch import fetch_alpha
from storage.store_sim import store_sim, utc_text

API_BASE = "https://api.worldquantbrain.com"
plog = get_file_logger("poll")

FETCH_RETRIES = 3
FETCH_BACKOFF_SEC = 1.0
FETCH_TIMEOUT_SEC = 20


def _already_processed(conn, child_id):
    """True when this child needs no further work.

    A stored child row is final when it is not a successful sim (nothing else
    to fetch), or when its alpha was already stored. A COMPLETE child whose
    alpha is still missing (transient alpha GET failure) is re-fetched.
    """
    row = conn.execute("SELECT status, alpha_id FROM simulations WHERE sim_id=?", (child_id,)).fetchone()
    if not row:
        return False
    status, alpha_id = row
    if status not in ("COMPLETE", "WARNING"):
        return True
    if not alpha_id:
        return False
    have_alpha = conn.execute("SELECT 1 FROM alpha_results WHERE alpha_id=?", (alpha_id,)).fetchone()
    return bool(have_alpha)


def fetch_child(session, info, child_id, i, total, expr, conn, settings, now):
    """Fetch one child simulation, store sim and alpha.

    Returns (ok, err, fetched): `fetched` is False only when the child response
    could not be obtained, so the caller keeps the batch in flight for a retry.
    """
    child = None
    for attempt in range(FETCH_RETRIES):
        try:
            child_resp = session.get(f"{API_BASE}/simulations/{child_id}", timeout=FETCH_TIMEOUT_SEC)
            if child_resp.status_code == 200:
                child = child_resp.json()
                break
            plog.warning(
                "B%d child %s: HTTP %d (att %d/%d)",
                info["idx"],
                child_id,
                child_resp.status_code,
                attempt + 1,
                FETCH_RETRIES,
            )
        except Exception as e:
            plog.warning(
                "B%d child %s: fetch/parse error (att %d/%d): %s",
                info["idx"],
                child_id,
                attempt + 1,
                FETCH_RETRIES,
                e,
            )
        if attempt < FETCH_RETRIES - 1:
            time.sleep(FETCH_BACKOFF_SEC * (attempt + 1))

    if child is None:
        if _already_processed(conn, child_id):
            plog.debug("B%d child %s: fetch failed but already stored; treating as fetched", info["idx"], child_id)
            return 0, 0, True
        return 0, 1, False

    status = child.get("status", "UNKNOWN")
    alpha_id = child.get("alpha")
    plog.debug("B%d child %d/%d: %s alpha=%s expr=%s", info["idx"], i + 1, total, status, alpha_id, (expr or "")[:50])

    store_sim(
        conn,
        child_id,
        info["pid"],
        info["idx"],
        expr,
        settings["region"],
        settings["universe"],
        settings["delay"],
        status,
        alpha_id,
        child.get("message"),
        settings,
        now,
        # The batch's submission instant, so the row can be timed. See
        # `store_sim`: the column was NULL for every row until 2026-10-12.
        submitted_at=utc_text(info.get("submitted_at")),
    )

    if alpha_id and status in ("COMPLETE", "WARNING"):
        ok, err = fetch_alpha(session, info, alpha_id, conn, expr, settings, child_id)
        return ok, err, bool(ok)

    return 0, 1, True
