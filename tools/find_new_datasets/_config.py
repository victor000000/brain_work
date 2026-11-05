"""Path/constant config for find_new_datasets."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(_HERE))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


from core.db import DB_PATH as DB_PATH  # noqa: E402
from core.log_config import LOG_DIR  # noqa: E402  (single definition)

LOG_PATH = os.path.join(LOG_DIR, "find_new_datasets.log")
os.makedirs(LOG_DIR, exist_ok=True)

# Fields per page in the per-(region, universe, delay, subcategory) scan.
PAGE_LIMIT = 50

# Safety cap on pages per combo, so a bad `count` cannot walk forever. At 50
# fields/page this is 2000 fields for one (region, universe, delay, subcategory).
MAX_PAGES = 40
