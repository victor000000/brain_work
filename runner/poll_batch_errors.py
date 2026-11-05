"""Terminal batch errors: persist the sim error and mark the parent ERROR.

Split out of `runner/poll_batch.py`, which re-exports these names. This is
bookkeeping only — it must never raise into the poll loop.
"""

from core.log import get_file_logger
from storage.store_sim import _record_error, update_sim_status

plog = get_file_logger("poll")

# Body statuses that mean the platform gave up on the batch.
_ERROR_STATUSES = ("ERROR", "FAIL", "FAILED")

# A batch younger than this is never written off on a no-result body: the
# platform returns one for freshly submitted batches whose children are still
# being created (their list appears a minute or two later).
MIN_ERROR_AGE_SEC = 240


def _record_batch_error(conn, info, message, now):
    """Persist a terminal batch error (sim_errors + simulations row)."""
    settings = info.get("settings") or {}
    exprs = info.get("exprs") or []
    try:
        _record_error(
            conn,
            exprs[0] if exprs else None,
            settings.get("region"),
            message,
            settings,
            now,
            sim_id=info.get("pid"),
        )
        update_sim_status(conn, info["pid"], "ERROR", error_msg=message[:500], ts=now)
    except Exception as e:  # never let error bookkeeping kill the poll loop
        # %s, not %d: `.get` without a default is exactly the case where `idx`
        # might be absent, and `%d` with None raises inside logging — which is
        # the one thing this handler may not do, since it is the last line of
        # defence for a batch whose error we failed to record.
        plog.warning("B%s: failed to record batch error: %s", info.get("idx"), e)
