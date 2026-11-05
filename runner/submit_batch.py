"""Submit a multi-sim batch to BRAIN API.

Assembles payload, delegates retry to brain_api_retry,
checks budget, stores parent sim, returns batch info.

The post-201 half (Location parsing, parent row, success log) lives in
`submit_store` and is re-exported here so `from runner.submit_batch import
...` keeps working.
"""

import logging

from core.api_retry import post_simulation
from core.budget import update_from_headers
from runner.submit_batch_log import log_batch_settings
from runner.submit_store import (  # noqa: F401
    API_BASE,
    store_accepted_batch,
)

try:  # core/budget gained read_remaining; fall back to a local reader until then.
    from core.budget import read_remaining
except ImportError:  # pragma: no cover - exercised only against older core

    def read_remaining(resp):
        """Remaining sim budget from X-Ratelimit-Remaining, or None if unknown."""
        raw = resp.headers.get("X-Ratelimit-Remaining")
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None


log = logging.getLogger("brain")


def submit_batch(session, expressions, settings, batch_idx, conn, *, on_definitely_unsubmitted=None):
    """Submit expressions as multi-sim batch. Returns batch info or None."""
    # Build payload -- array for multi-sim, single object for 1
    items = [{"type": "REGULAR", "settings": settings, "regular": e} for e in expressions]
    payload = items[0] if len(items) == 1 else items

    log_batch_settings(batch_idx, expressions, settings)

    # Submit with retry
    if on_definitely_unsubmitted is None:
        resp = post_simulation(session, payload, batch_idx)
    else:
        resp = post_simulation(session, payload, batch_idx, on_definitely_unsubmitted=on_definitely_unsubmitted)
    if resp is None:
        return None
    if resp == "CONCURRENT":
        return "CONCURRENT"  # caller should wait for in-flight to finish
    if resp == "BUDGET":
        return "BUDGET"  # caller should sleep until reset

    # A 201 means BRAIN accepted the batch and it is now running. From here on
    # it MUST be stored so the poll loop can find it — losing it burns quota
    # and leaks a concurrent slot.
    remaining = read_remaining(resp)
    update_from_headers(resp.headers)
    return store_accepted_batch(conn, resp, expressions, settings, batch_idx, remaining)
