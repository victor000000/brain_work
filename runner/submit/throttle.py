"""Per-cell throttle cooldown and the held-alpha queues.

Split out of `runner/submit/flow.py`, which re-exports these names. The two
dicts are the state, not a copy of it: `flow` imports the same objects, so the
test helper and the drain path keep seeing one queue per cell.
"""

import time
from collections import defaultdict, deque

# Throttle-aware pacing. Per-cell sliding window of throttle events;
# if the count within THROTTLE_WINDOW_SEC reaches THROTTLE_THRESHOLD,
# the cell enters cooldown and new submits are held.
THROTTLE_WINDOW_SEC = 60
THROTTLE_THRESHOLD = 5
COOLDOWN_SEC = 120
QUEUE_LIMIT = 50

_throttle_events: dict[tuple[str, str, int], deque[float]] = defaultdict(deque)
_held_alphas: dict[tuple[str, str, int], deque[str]] = defaultdict(deque)


def _reset_throttle_state() -> None:
    """Test helper — clear all throttle/held state. Production never calls this."""
    _throttle_events.clear()
    _held_alphas.clear()


def record_throttle(cell: tuple[str, str, int], now: float | None = None) -> None:
    """Append a throttle event for `cell` at `now` (defaults to time.time())."""
    if now is None:
        now = time.time()
    _throttle_events[cell].append(now)


def in_cooldown(cell: tuple[str, str, int], now: float | None = None) -> bool:
    """True if `cell` has THROTTLE_THRESHOLD or more events in the last window.

    Side-effect: prunes stale events older than THROTTLE_WINDOW_SEC.
    """
    if now is None:
        now = time.time()
    events = _throttle_events[cell]
    while events and now - events[0] > THROTTLE_WINDOW_SEC:
        events.popleft()
    return len(events) >= THROTTLE_THRESHOLD


def queue_held_alpha(cell: tuple[str, str, int], alpha_id: str) -> None:
    """Hold an alpha_id for later submit. FIFO; oldest dropped on overflow."""
    q = _held_alphas[cell]
    if len(q) >= QUEUE_LIMIT:
        q.popleft()
    q.append(alpha_id)


def drain_held_alpha(cell: tuple[str, str, int]) -> str | None:
    """Pop the next held alpha for `cell`, or None if the queue is empty."""
    q = _held_alphas[cell]
    if not q:
        return None
    return q.popleft()
