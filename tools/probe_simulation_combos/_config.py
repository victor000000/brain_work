"""Path/constant config for probe_simulation_combos."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(_HERE))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

API_BASE = "https://api.worldquantbrain.com"

from core.log_config import LOG_DIR  # noqa: E402  (single definition)

LOG_PATH = os.path.join(LOG_DIR, "probe_simulation_combos.log")
RESULT_PATH = os.path.join(LOG_DIR, "probe_simulation_combos.json")
DISCOVERY_JSON = os.path.join(LOG_DIR, "discover_universes.json")
os.makedirs(LOG_DIR, exist_ok=True)

# Throttle between probes — keep low so the run finishes in reasonable time
# even with the simulator stopped.
THROTTLE_SECONDS = 1.5

# Backoff schedule on 429 — broad enough to clear most transient throttling.
RETRY_429_MAX = 6
RETRY_429_BACKOFF = (8, 12, 16, 24, 32, 48)
