"""Pacing signals from one poll: non-200 handling and Retry-After on a 200.

Split out of `runner/poll_batch.py`, which re-exports these names. Both
functions are advisory — they record `retry_after`/`poll_throttled`/`progress`
on the batch and report whether the poll is finished, never raising.
"""

import time

from core.log import get_file_logger
from runner.http_retry import parse_retry_after

plog = get_file_logger("poll")

# Cap a single poll's reported retry so a bogus header cannot park a batch.
MAX_RETRY_AFTER_SEC = 600


def _note_not_200(info, resp, age):
    """Record a non-200 poll's pacing signals; always False (still running)."""
    retry = parse_retry_after(resp.headers) if resp.status_code == 429 else None
    if retry is not None:
        info["retry_after"] = min(retry, MAX_RETRY_AFTER_SEC)
    if resp.status_code == 429:
        # Pacing signal for the loop; do not stale-drop while throttled.
        info["poll_throttled"] = True
    else:
        # A non-429 response means we are being served again: clear the
        # throttle flag too, or drop_stale() would defer forever.
        info.pop("retry_after", None)
        info.pop("poll_throttled", None)
    plog.warning(
        "B%d poll: HTTP %d (not 200) age=%.0fs retry=%s %s/%s",
        info["idx"],
        resp.status_code,
        age,
        retry,
        info["settings"]["region"],
        info["settings"]["universe"],
    )
    return False


def _still_running(info, resp, data, age):
    """Handle Retry-After on a 200; True while the batch is still running."""
    # Retry-After is also legal on a 200 while the batch is still running.
    retry = parse_retry_after(resp.headers)
    if not (retry and retry > 0):
        return False
    info["retry_after"] = min(retry, MAX_RETRY_AFTER_SEC)
    info.pop("poll_throttled", None)
    progress = (data.get("progress") or 0) * 100
    # Remember forward motion for the stale-drop decision: a batch still
    # climbing is working, however old it is.
    if progress > info.get("progress", -1):
        info["last_advance_at"] = time.time()
    info["progress"] = progress
    plog.debug(
        "B%d: %.0f%% retry=%.1fs age=%.0fs %s/%s",
        info["idx"],
        progress,
        retry,
        age,
        info["settings"]["region"],
        info["settings"]["universe"],
    )
    if age > 600:
        plog.warning(
            "B%d SLOW: %.0f%% after %.0fs %s/%s",
            info["idx"],
            progress,
            age,
            info["settings"]["region"],
            info["settings"]["universe"],
        )
    return True
