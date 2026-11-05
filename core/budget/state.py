"""BudgetState class + singleton + thread-safe accessors.

State is encapsulated so background threads (e.g. the auto-checker running
concurrently with the explore loop) can mutate safely via an internal RLock.

The exhaustion window lives in `core.budget.state_exhaustion`, the shared JSON
file in `core.budget.state_persist` (its helpers in `core.budget.state_file`);
they are re-exported here so every `from core.budget.state import ...` keeps
resolving for callers and tests.
"""

import threading

from core.budget.state_exhaustion import ExhaustionMixin
from core.budget.state_file import (  # noqa: F401
    DEFAULT_RESET_SECONDS,
    MAX_RESET_WINDOW_SEC,
    MIN_RESET_SECONDS,
    _live_reset_at,
    _read_state_file,
    _sane_reset_seconds,
    _state_path,
)
from core.budget.state_persist import PersistenceMixin

# Exhaust only at zero. The explorer serializes single-expression requests
# near the daily limit, because concurrent simulation charges settle late.
BUDGET_FLOOR = 1


class BudgetState(ExhaustionMixin, PersistenceMixin):
    """Mutable budget tracker. One singleton lives at module scope; tests can
    construct fresh instances and inject them via `set_state()`.

    Only the singleton sets persist=True, so throwaway instances in tests
    never touch the shared file.
    """

    def __init__(self, persist=False):
        self.last_reset_seconds = 60
        self.last_remaining = None
        self._exhausted = False
        self._reset_at = 0.0
        self._lock = threading.RLock()
        self._persist = persist

    def reset(self):
        with self._lock:
            self.last_reset_seconds = 60
            self.last_remaining = None
            self._exhausted = False
            self._reset_at = 0.0
            # An explicit reset is deliberate operator intent: it clears the
            # shared window too, so no merge-back may resurrect it.
            self._persist_state(merge_shared=False)

    def note_remaining(self, remaining):
        """Record the last-seen X-Ratelimit-Remaining for cross-process visibility."""
        with self._lock:
            if remaining == self.last_remaining:
                return
            self.last_remaining = remaining
            self._persist_state()

    def submission_capacity(self, maximum):
        """Fit a request to the known allowance; unknown permits a normal batch."""
        with self._lock:
            if self.is_exhausted():
                return 0
            if self.last_remaining is None:
                return maximum
            return max(0, min(maximum, self.last_remaining))


_state = BudgetState(persist=True)
_state.load_persisted_state()


def get_state() -> BudgetState:
    """Return the active singleton state — useful for direct attribute access."""
    return _state


def set_state(state: BudgetState) -> None:
    """Replace the active state (tests only — not safe in production)."""
    global _state
    _state = state
