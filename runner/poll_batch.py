"""Poll a submitted batch for completion.

The HTTP/JSON step lives in `runner.poll_batch_io`, the pacing signals in
`runner.poll_batch_pace`, the terminal-error bookkeeping in
`runner.poll_batch_errors`, the no-result decision in
`runner.poll_batch_writeoff` and the result storing in
`runner.poll_batch_results`; all are re-exported here so
`from runner.poll_batch import ...` keeps working for callers and tests.
"""

import time

from runner.poll_batch_errors import (  # noqa: F401
    _ERROR_STATUSES,
    MIN_ERROR_AGE_SEC,
    _record_batch_error,
)
from runner.poll_batch_io import (  # noqa: F401
    _fetch,
    _parse_json,
    log,
    plog,
)
from runner.poll_batch_pace import (  # noqa: F401
    MAX_RETRY_AFTER_SEC,
    _note_not_200,
    _still_running,
)
from runner.poll_batch_results import _poll_multi, _poll_single
from runner.poll_batch_writeoff import _write_off_no_result
from runner.poll_children import handle_children  # noqa: F401
from runner.poll_single import handle_single  # noqa: F401


def poll_batch(session, info, conn):
    """Poll a batch for completion. Returns True if finished (success or error)."""
    age = time.time() - info.get("submitted_at", time.time())
    resp = _fetch(session, info, age)
    if resp is None:
        return False

    if resp.status_code != 200:
        return _note_not_200(info, resp, age)

    data = _parse_json(info, resp, age)
    if data is None:
        return False

    if _still_running(info, resp, data, age):
        return False

    # The parent answered without `Retry-After`, so it has left the computing
    # phase — that state change is itself an advance and has to be recorded.
    # `last_advance_at` is otherwise written only by `_still_running`, which
    # this poll does not reach, so a batch that finished computing kept a
    # last-advance timestamp from minutes earlier while its children were being
    # fetched and read as frozen: `drop_stale` aborts on it once the age has
    # crossed `STALE_TIMEOUT`. Measured 2026-10-08/09: B682 was dropped as
    # "last progress 1169s ago" 64 seconds after a poll had 9/10 of its
    # children in hand, and B226 the same at 244 seconds. The fetch phase holds
    # no BRAIN slot — BRAIN refuses the DELETE precisely because the
    # simulation is complete — so a drop here frees nothing.
    info["last_advance_at"] = time.time()
    info.pop("retry_after", None)
    info.pop("poll_throttled", None)

    settings = info["settings"]
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    children = data.get("children") or []
    alpha_id = data.get("alpha")
    status = (data.get("status") or "").upper()

    no_result = _write_off_no_result(conn, info, data, status, children, alpha_id, age, now)
    if no_result is not None:
        return no_result
    info.pop("error_strikes", None)

    # Single sim: alpha directly on parent response
    if not children and alpha_id:
        return _poll_single(session, info, data, alpha_id, conn, settings, now, age)

    # Multi sim: iterate children
    return _poll_multi(session, info, children, conn, settings, now, age)
