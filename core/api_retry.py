"""Simulation POST pacing without repeating an uncertain request.

Concurrent/budget rejections return to the owner; explicit transient429
rejections may retry. A transport failure or5xx cannot prove rejection, so
stop immediately and preserve the payload/claim for reconciliation. BRAIN
provides no idempotency key; even a bounded retry can create duplicate jobs.
"""

import json
import time  # noqa: F401 - compatibility surface for retry-clock test patches

import core.budget as budget
from core.api_retry_headers import (  # noqa: F401
    RATE_LIMIT_WAIT,
    _give_up,
    _log_response,
    _reset_seconds,
    _retry_after_seconds,
)
from core.api_retry_limits import BUDGET_RESET_THRESHOLD, _handle_429  # noqa: F401
from core.log import get_file_logger

API_BASE = "https://api.worldquantbrain.com"
slog = get_file_logger("submit")

MAX_RETRIES = 3  # Only explicit transient429 rejections may consume another attempt.

# These responses reject the request before creating a simulation. Other
# non-201 responses (notably 2xx, 408 and gateway failures) cannot establish
# that nothing was accepted, so they must not refund a claimed candidate.
DEFINITE_REJECTION_STATUSES = frozenset({400, 401, 403, 404, 405, 409, 413, 415, 422})


def _notify_unsubmitted(callback, possibly_accepted=False):
    if callback is not None and not possibly_accepted:
        callback()


def _uncertain(payload, batch_idx, reason):
    """Keep the full request in the durable local log, without another POST."""
    slog.error(
        "B%d: simulation POST outcome UNKNOWN; no retry; reason=%s payload=%s",
        batch_idx,
        reason,
        json.dumps(payload, sort_keys=True, default=str),
    )
    return None


def post_simulation(session, payload, batch_idx, *, on_definitely_unsubmitted=None):
    """POST once unless an explicit transient429 proves rejection.

    Return response, None, 'CONCURRENT' or 'BUDGET'. A timeout,5xx or other
    ambiguous status must not refund reservations or cause another POST.
    Existing probe/polish ownership remains intact across restart.
    """
    if budget.is_exhausted():
        slog.debug("B%d: budget known exhausted (%ds left), skipping", batch_idx, budget.seconds_until_reset())
        _notify_unsubmitted(on_definitely_unsubmitted)
        return "BUDGET"

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.post(f"{API_BASE}/simulations", json=payload)
        except Exception as error:
            return _uncertain(payload, batch_idx, str(error))

        _log_response(resp, batch_idx, attempt)
        if resp.status_code == 201:
            return resp
        if resp.status_code == 429:
            action = _handle_429(resp, batch_idx, attempt)
            if action is None:
                continue
            _notify_unsubmitted(on_definitely_unsubmitted)
            return action
        if resp.status_code in DEFINITE_REJECTION_STATUSES:
            _notify_unsubmitted(on_definitely_unsubmitted)
            return _give_up(resp, batch_idx)
        return _uncertain(payload, batch_idx, f"HTTP{resp.status_code}; Location={resp.headers.get('Location', '')}")

    slog.error("B%d: explicit rate-limit rejection after %d attempts", batch_idx, MAX_RETRIES)
    _notify_unsubmitted(on_definitely_unsubmitted)
    return None
