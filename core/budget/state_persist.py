"""Durable copy of the budget state: write-merge and load-back.

Split out of `core/budget/state.py`, which mixes these methods into
BudgetState. Writes are atomic (tmp file + os.replace) and a corrupt or
missing file is ignored.
"""

import contextlib
import json
import os
import tempfile
import time

from core.budget.state_file import (
    MIN_RESET_SECONDS,
    _live_reset_at,
    _read_state_file,
    _state_path,
)
from core.log import get_file_logger

blog = get_file_logger("budget")


class PersistenceMixin:
    """Keep the exhaustion window in the shared JSON state file."""

    def _persist_state(self, merge_shared=True):
        if not self._persist:
            return
        path = _state_path()
        with self._lock:
            now = time.time()
            exhausted = self._exhausted and now < self._reset_at
            reset_at = self._reset_at
            last_reset_seconds = self.last_reset_seconds
            if merge_shared:
                # Read-merge-write: another process may already hold a longer,
                # still-running window (e.g. the daily quota, while this one
                # only ever saw a transient 429). Writing our own shorter state
                # would erase it from the shared file — and a restart would
                # then believe the budget is healthy and burn the remaining
                # quota. Adopt the longer window instead.
                shared_reset_at = _live_reset_at(_read_state_file(path), now)
                if shared_reset_at > max(reset_at, now):
                    self._exhausted = True
                    self._reset_at = shared_reset_at
                    self.last_reset_seconds = max(int(shared_reset_at - now), MIN_RESET_SECONDS)
                    exhausted = True
                    reset_at = shared_reset_at
                    last_reset_seconds = self.last_reset_seconds
            payload = {
                "exhausted": exhausted,
                "reset_at": reset_at,
                "last_reset_seconds": last_reset_seconds,
                "last_remaining": self.last_remaining,
                "updated_at": now,
            }
        try:
            directory = os.path.dirname(path) or "."
            os.makedirs(directory, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".budget_state.", suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(payload, f)
                os.replace(tmp_path, path)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise
        except Exception as err:  # never let bookkeeping break the engine
            blog.debug("Budget state persist failed: %s", err)

    def load_persisted_state(self):
        """Load a previous process's exhaustion flag, if still within its window."""
        if not self._persist:
            return
        path = _state_path()
        data = _read_state_file(path)
        if data is None:
            return  # missing or corrupt → start clean
        now = time.time()
        reset_at = _live_reset_at(data, now)
        remaining = data.get("last_remaining")
        if isinstance(remaining, bool) or not isinstance(remaining, int):
            remaining = None
        if not reset_at and remaining is not None and remaining <= 0:
            # A previous window's zero is not the new day's allowance. This
            # also repairs files written before reset cleared that observation.
            remaining = None
        seconds = data.get("last_reset_seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, int):
            seconds = None
        with self._lock:
            self.last_remaining = remaining
            if reset_at > now:
                self._exhausted = True
                self._reset_at = reset_at
                self.last_reset_seconds = (
                    seconds if seconds is not None else max(int(reset_at - now), MIN_RESET_SECONDS)
                )
                blog.info("Restored budget exhaustion from %s (%ds left)", path, self.seconds_until_reset())
