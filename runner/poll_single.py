"""Handle single-sim poll response (no children, alpha on parent)."""

from core.log import get_file_logger
from storage.store_alpha import store_alpha

API_BASE = "https://api.worldquantbrain.com"
plog = get_file_logger("poll")

FETCH_TIMEOUT_SEC = 20


def handle_single(session, info, data, conn, settings):
    """Handle single-sim response (no children, alpha on parent).

    Returns (ok, err, complete); complete is False when the alpha could not be
    stored, so the batch stays in flight and is re-polled.
    """
    expr = info["exprs"][0] if info["exprs"] else "?"
    try:
        resp = session.get(f"{API_BASE}/alphas/{data['alpha']}", timeout=FETCH_TIMEOUT_SEC)
        plog.debug("B%d alpha %s: HTTP %d", info["idx"], data["alpha"], resp.status_code)
        if resp.status_code == 200:
            alpha_data = resp.json()
            store_alpha(
                conn,
                info["pid"],
                expr,
                settings["region"],
                settings["universe"],
                settings["delay"],
                settings,
                alpha_data,
            )
            # The same INFO line `poll_alpha_fetch.fetch_alpha` writes for a
            # child, and for the same reason: it is the only record linking a
            # batch index to the alpha it produced, and `tools.progress_from_log`
            # joins polish batches to their results on it. Without it every
            # single-expression batch — which is what every polish batch is —
            # reported "0 produced: no results yet" for the rest of the day,
            # however long ago it had finished. Measured 2026-10-09: B584
            # completed and stored `omWawNWl` at 01:43:33 and `make progress`
            # still showed it empty at 11:10, because the only line poll.log
            # carried for it was the DEBUG "HTTP 200" above.
            #
            # Written after `store_alpha` rather than before, so the line means
            # "this alpha is in the database" — a store that raises must not
            # report a result the progress summary would then count.
            plog.info(
                "B%d alpha %s: sharpe=%.2f %s/%s",
                info["idx"],
                data["alpha"],
                alpha_data.get("is", {}).get("sharpe") or 0,
                settings["region"],
                settings["universe"],
            )
            return 1, 0, True
        else:
            plog.warning(
                "B%d alpha %s: HTTP %d (not 200)",
                info["idx"],
                data["alpha"],
                resp.status_code,
            )
    except Exception as e:
        plog.warning("B%d single alpha fetch error: %s", info["idx"], e)
    return 0, 1, False
