"""Paths, logging and pv/option identification for the field refresh tool.

Split out of `tools/refresh_pv_option_fields.py`, which re-exports these names
so the CLI and any importer keep working. The logger is named "dl" with the
same two handlers (stdout at INFO, file at DEBUG) as before the split.
"""

import logging
import os
import sys

from core.log_config import LOG_DIR
from download.fetch_fields import REGION_CONFIG

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")

os.makedirs(LOG_DIR, exist_ok=True)

log = logging.getLogger("dl")
log.setLevel(logging.DEBUG)
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_ch)
_fh = logging.FileHandler(os.path.join(LOG_DIR, "refresh_pv_option.log"), mode="a")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(message)s"))
log.addHandler(_fh)

PV_OPT_PREFIXES = ("pv-", "option-")


def is_pv_option(subcategory_id: str) -> bool:
    """True for the five pv/option subcategories (pv-price-volume, option-option, ...)."""
    return subcategory_id.startswith(PV_OPT_PREFIXES)


def count_combos() -> int:
    return sum(len(c["universes"]) * len(c["delays"]) for c in REGION_CONFIG.values())
