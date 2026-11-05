"""HTTP fetch and JSON parse for one poll pass.

Split out of `runner/poll_batch.py`, which re-exports these names. A transport
error or an unparseable 200 body only defers the batch: both re-poll later, so
neither is allowed to raise out of the poll loop.
"""

import logging

from core.log import get_file_logger

log = logging.getLogger("brain")
plog = get_file_logger("poll")


def _fetch(session, info, age):
    """GET the batch location; None when the request itself raised."""
    try:
        resp = session.get(info["loc"], timeout=30)
        plog.debug("B%d poll: HTTP %d len=%d age=%.0fs", info["idx"], resp.status_code, len(resp.content), age)
        return resp
    except Exception as e:
        log.warning("B%d: poll connection error: %s", info["idx"], e)
        plog.warning("B%d: poll connection error (age=%.0fs): %s", info["idx"], age, e)
        return None


def _parse_json(info, resp, age):
    """Parse a 200 body; None when it is empty or malformed."""
    try:
        return resp.json()
    except Exception as e:
        plog.warning(
            "B%d poll: empty/bad JSON (HTTP %d, %d bytes): %s",
            info["idx"],
            resp.status_code,
            len(resp.content),
            e,
        )
        return None
