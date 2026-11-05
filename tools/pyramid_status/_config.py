"""Path and constant config for pyramid_status."""

import os
import sys

# Ensure project root is on sys.path so `core.*` imports resolve when the
# package is invoked as `python3 -m tools.pyramid_status`.
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(_HERE))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

API_BASE = "https://api.worldquantbrain.com"


from core.db import DB_PATH as DB_PATH  # noqa: E402
from core.log_config import LOG_DIR  # noqa: E402  (single definition)

LOG_PATH = os.path.join(LOG_DIR, "pyramid_status.log")
RESULT_PATH = os.path.join(LOG_DIR, "pyramid_status.json")
os.makedirs(LOG_DIR, exist_ok=True)

# All alpha-lifecycle statuses we routinely fetch.
DEFAULT_STATUSES = ["ACTIVE", "ONBOARDING", "DECOMMISSIONED", "PROD", "OUT_OF_SAMPLE", "EXPIRED"]

# Throttle between detail fetches to stay under BRAIN's per-second limit.
THROTTLE = 0.6
PAGE_SIZE = 50

# Multiplier strictly greater than this counts as a BRAIN-incentivized pyramid.
ACTIVE_THRESHOLD = 1.0
