"""Path/constant config for apply_discovery_and_redownload."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(_HERE))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# The canonical (region, universe, delay) matrix. download/fetch_fields.py only
# derives its REGION_CONFIG from this file, so this is the only place a patch
# can land.
REGIONS_PATH = os.path.join(PROJECT_DIR, "core", "regions.py")

from core.db import DB_PATH as DB_PATH  # noqa: E402
from core.log_config import LOG_DIR  # noqa: E402  (single definition)

DISCOVERY_JSON = os.path.join(LOG_DIR, "discover_universes.json")
LOG_PATH = os.path.join(LOG_DIR, "apply_discovery.log")
os.makedirs(LOG_DIR, exist_ok=True)
