"""Path/constant config for discover_simulation_matrix."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(_HERE))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

API_BASE = "https://api.worldquantbrain.com"

from core.log_config import LOG_DIR  # noqa: E402  (single definition)

LOG_PATH = os.path.join(LOG_DIR, "discover_simulation_matrix.log")
LEGACY_RESULT_PATH = os.path.join(LOG_DIR, "discover_universes.json")
FULL_RESULT_PATH = os.path.join(LOG_DIR, "discover_simulation_matrix.full.json")
os.makedirs(LOG_DIR, exist_ok=True)
