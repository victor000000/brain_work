"""Fetch and store alpha data from BRAIN API for a completed child sim."""

import time

from core.log import get_file_logger
from storage.store_alpha import store_alpha

API_BASE = "https://api.worldquantbrain.com"
plog = get_file_logger("poll")

FETCH_RETRIES = 3
FETCH_BACKOFF_SEC = 1.0
FETCH_TIMEOUT_SEC = 20


def fetch_alpha(session, info, alpha_id, conn, expr, settings, child_id):
    """Fetch and store alpha data for a child. Returns (ok, err) counts.

    Transient GET failures are retried with backoff so a single blip does not
    permanently lose the alpha.
    """
    for attempt in range(FETCH_RETRIES):
        try:
            alpha_resp = session.get(f"{API_BASE}/alphas/{alpha_id}", timeout=FETCH_TIMEOUT_SEC)
            plog.debug("B%d alpha %s: HTTP %d", info["idx"], alpha_id, alpha_resp.status_code)
            if alpha_resp.status_code == 200:
                alpha_data = alpha_resp.json()
                sharpe = alpha_data.get("is", {}).get("sharpe", 0)
                plog.info(
                    "B%d alpha %s: sharpe=%.2f %s/%s",
                    info["idx"],
                    alpha_id,
                    sharpe or 0,
                    settings["region"],
                    settings["universe"],
                )
                store_alpha(
                    conn,
                    child_id,
                    expr,
                    settings["region"],
                    settings["universe"],
                    settings["delay"],
                    settings,
                    alpha_data,
                )
                return 1, 0
            plog.warning(
                "B%d alpha %s: HTTP %d (att %d/%d)",
                info["idx"],
                alpha_id,
                alpha_resp.status_code,
                attempt + 1,
                FETCH_RETRIES,
            )
        except Exception as e:
            plog.warning(
                "B%d alpha %s fetch error (att %d/%d): %s",
                info["idx"],
                alpha_id,
                attempt + 1,
                FETCH_RETRIES,
                e,
            )
        if attempt < FETCH_RETRIES - 1:
            time.sleep(FETCH_BACKOFF_SEC * (attempt + 1))
    return 0, 1
