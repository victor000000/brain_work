"""Where the shared budget-state file lives, and how its contents are read.

Split out of `core/budget/state.py`, which re-exports these helpers. The
module-level singleton persists its exhaustion flag (plus the last-seen
remaining/reset) to this small JSON file so separate processes/tools share it
across restarts; a corrupt or missing file is ignored.
"""

import json
import math
import os

from core.log_config import LOG_DIR

# Bounds for an exhaustion window. BRAIN's simulation quota resets daily, so
# no legitimate window is longer than 24h: a malformed/hostile header (or a
# badly skewed clock in a persisted file) claiming one must not park the
# engine until the year 3000. The floor mirrors the old mark_exhausted() clamp.
MIN_RESET_SECONDS = 30
MAX_RESET_WINDOW_SEC = 24 * 3600
DEFAULT_RESET_SECONDS = 60


def _state_path():
    """Path of the shared budget-state file (env override wins)."""
    override = os.environ.get("BRAIN_BUDGET_STATE_PATH")
    if override:
        return override
    return os.path.join(LOG_DIR, ".budget_state.json")


def _read_state_file(path):
    """Load the shared state dict, or None when missing/corrupt/unreadable."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _live_reset_at(data, now):
    """The still-running exhaustion window recorded in `data`, else 0.0.

    Only an unexpired, finite, plausible window counts: a corrupt file or a
    clock skewed far into the future must not be trusted.
    """
    if not isinstance(data, dict) or not data.get("exhausted"):
        return 0.0
    try:
        reset_at = float(data.get("reset_at", 0))
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(reset_at) or reset_at <= now:
        return 0.0
    if reset_at - now > MAX_RESET_WINDOW_SEC:
        return 0.0
    return reset_at


def _sane_reset_seconds(raw):
    """Coerce a reset hint (header string, number, None) into a sane window.

    Never raises. Unparseable or non-finite values fall back to the default
    window, and an absurdly long one is clamped to MAX_RESET_WINDOW_SEC so a
    bogus header cannot mark the budget exhausted for years.
    """
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_RESET_SECONDS
    if not math.isfinite(seconds):
        return DEFAULT_RESET_SECONDS
    return int(min(max(seconds, MIN_RESET_SECONDS), float(MAX_RESET_WINDOW_SEC)))
