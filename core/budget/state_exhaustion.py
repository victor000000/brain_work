"""The exhaustion window: its flag, its deadline and how it is extended.

Split out of `core/budget/state.py`, which mixes these methods into
BudgetState. The window is bounded (see `core.budget.state_file`) so a
malformed header can never park the engine for years.
"""

import time

from core.budget.state_file import _sane_reset_seconds
from core.log import get_file_logger

blog = get_file_logger("budget")


class ExhaustionMixin:
    """Flag + reset deadline, guarded by the state's RLock."""

    def is_exhausted(self):
        with self._lock:
            if self._exhausted and time.time() >= self._reset_at:
                self._exhausted = False
                self.last_remaining = None
                blog.info("Budget reset time reached, clearing exhaustion flag")
                self._persist_state()
            return self._exhausted

    def seconds_until_reset(self):
        with self._lock:
            if not self._exhausted or time.time() >= self._reset_at:
                return 0
            return max(0, int(self._reset_at - time.time()))

    def mark_exhausted(self, reset_seconds):
        with self._lock:
            # Sanitized here (not at the call sites) so every header path —
            # submit, 429 retry, auto-check — is safe against a malformed
            # value such as "inf", "nan", "?" or an absurd number.
            new_seconds = _sane_reset_seconds(reset_seconds)
            new_reset_at = time.time() + new_seconds
            self._exhausted = True
            if new_reset_at > self._reset_at:
                self._reset_at = new_reset_at
                self.last_reset_seconds = new_seconds
                blog.warning(
                    "Budget exhausted, resets in %ds (at %.0f)",
                    new_seconds,
                    new_reset_at,
                )
            else:
                # A shorter later reset (e.g. a transient 429 after a daily
                # exhaustion) must not shorten a longer known window.
                blog.info(
                    "Budget already exhausted until %.0f; ignoring shorter reset (%ds)",
                    self._reset_at,
                    new_seconds,
                )
            self._persist_state()
