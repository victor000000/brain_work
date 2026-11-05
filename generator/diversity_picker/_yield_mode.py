"""BRAIN_YIELD_WEIGHTING env-var gate for the yield-mode picker."""

import os


def yield_mode_enabled() -> bool:
    """True when BRAIN_YIELD_WEIGHTING is set to a truthy value."""
    return os.environ.get("BRAIN_YIELD_WEIGHTING", "").strip() not in ("", "0", "false", "False")
