#!/usr/bin/env python3
"""Download pv/option data fields from WorldQuant BRAIN into DuckDB.

Out-of-scope subcategories are filtered before the first API call, so the
download spends its budget only on price and options data.

Usage: python3 -m download.brain_data   (from the project root)
"""

import logging
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

from core.log_config import LOG_DIR
from core.scope import keep_category
from download.db_schema import init_db
from download.fetch_fields import download_all_fields
from download.session import API_BASE, BrainSession
from download.storage import store_categories

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "brain_data.duckdb")
LOG_PATH = os.path.join(LOG_DIR, "download.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

log = logging.getLogger("dl")
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(ch)
fh = logging.FileHandler(LOG_PATH, mode="a")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(message)s"))
log.addHandler(fh)


def main():
    log.info("=" * 50)
    log.info("BRAIN Data Downloader")
    log.info("=" * 50)

    brain = BrainSession()
    brain.authenticate()
    conn = init_db(DB_PATH)

    log.info("Fetching categories...")
    resp = brain.get(f"{API_BASE}/data-categories")
    if resp.status_code != 200:
        log.error("Categories failed: %d", resp.status_code)
        sys.exit(1)
    categories = resp.json()
    store_categories(conn, categories)

    # Filter at the source: out-of-scope children would otherwise be fetched
    # (spending API budget) and written into download_log.
    all_subcats = [ch for cat in categories for ch in cat.get("children", [])]
    subcats = [ch for ch in all_subcats if keep_category(ch)]
    log.info(
        "%d in-scope subcategories of %d across %d categories",
        len(subcats),
        len(all_subcats),
        len(categories),
    )

    total = download_all_fields(brain, conn, subcats)

    cc = conn.execute("SELECT COUNT(*) FROM dataset_categories").fetchone()[0]
    dc = conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
    fc = conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0]
    uf = conn.execute("SELECT COUNT(DISTINCT id) FROM data_fields").fetchone()[0]
    conn.execute(
        "INSERT OR REPLACE INTO metadata VALUES (?,?)",
        ("last_download", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())),
    )
    conn.commit()

    log.info("=" * 50)
    log.info("Done! Categories=%d Datasets=%d Fields=%d Unique=%d New=%d", cc, dc, fc, uf, total)
    log.info("=" * 50)
    conn.close()


if __name__ == "__main__":
    main()
