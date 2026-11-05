"""Single-combo probe with 429 backoff and accepted-sim cancel.

Any accepted simulation is cancelled in a `finally`, so an unexpected status
(202, a 201 without Location), a classify error, or a Ctrl-C cannot leave a
live sim burning a slot and budget.
"""

import contextlib
import time

from tools.probe_simulation_combos._config import (
    API_BASE,
    RETRY_429_BACKOFF,
    RETRY_429_MAX,
)
from tools.probe_simulation_combos._log import log
from tools.probe_simulation_combos.classify import classify
from tools.probe_simulation_combos.payload import build_payload

# A simulation BRAIN accepted. Anything else (400s, 429) created nothing.
ACCEPTED_STATUSES = frozenset({200, 201, 202})


def _cancel(session, resp):
    """DELETE the simulation BRAIN created so it doesn't consume slot/budget."""
    loc = resp.headers.get("Location") or resp.headers.get("location")
    if not loc:
        log.warning("simulation accepted (HTTP %d) without a Location header — cannot cancel it", resp.status_code)
        return
    if not loc.startswith("http"):
        loc = f"{API_BASE}{loc}"
    with contextlib.suppress(Exception):
        session.delete(loc, timeout=10)


def probe_combo(session, region, universe, delay):
    """Submit a trivial sim, classify the response, cancel if accepted.

    The cancel runs from `finally`, so it also covers a classify error and an
    interrupt raised after the sim was accepted.
    """
    payload = build_payload(region, universe, delay)
    last_resp = None
    try:
        for attempt in range(RETRY_429_MAX + 1):
            resp = session.post(f"{API_BASE}/simulations", json=payload, timeout=20)
            last_resp = resp
            if resp.status_code != 429:
                break
            backoff = RETRY_429_BACKOFF[min(attempt, len(RETRY_429_BACKOFF) - 1)]
            log.debug("429 on %s/%s/d%d, backoff %ds (attempt %d)", region, universe, delay, backoff, attempt + 1)
            time.sleep(backoff)
        verdict, detail = classify(last_resp)
        return verdict, detail
    finally:
        if last_resp is not None and last_resp.status_code in ACCEPTED_STATUSES:
            _cancel(session, last_resp)
