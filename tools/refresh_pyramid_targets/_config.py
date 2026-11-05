"""Path/constant config for refresh_pyramid_targets."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(_HERE))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

API_BASE = "https://api.worldquantbrain.com"

DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")

from core.log_config import LOG_DIR  # noqa: E402  (single definition)

LOG_PATH = os.path.join(LOG_DIR, "refresh_pyramid_targets.log")
os.makedirs(LOG_DIR, exist_ok=True)
