"""Session/catalogue setup and teardown for the pv/option field refresh.

Split out of `tools/refresh_pv_option_fields.py`. The phases live here so the
CLI keeps its original log order; they take the live connection rather than
opening one of their own.
"""

import sys
import time

from download.db_schema import init_db
from download.fetch_fields import download_all_fields
from download.session import API_BASE, BrainSession
from download.storage import store_categories
from tools.refresh_pv_option_env import DB_PATH, PV_OPT_PREFIXES, is_pv_option, log


def open_and_select():
    """Authenticate, load the catalogue and pick the pv/option subcategories.

    Returns (brain, conn, pv_opt, stale) — `stale` is the number of
    download_log rows the pv/option entries cover.
    """
    brain = BrainSession()
    brain.authenticate()
    conn = init_db(DB_PATH)

    log.info("Fetching categories...")
    resp = brain.get(f"{API_BASE}/data-categories")
    if resp.status_code != 200:
        log.error("Categories failed: HTTP %d", resp.status_code)
        sys.exit(1)
    categories = resp.json()
    store_categories(conn, categories)

    subcats = [ch for cat in categories for ch in cat.get("children", [])]
    pv_opt = [s for s in subcats if is_pv_option(s["id"])]
    skipped = [s["id"] for s in subcats if not is_pv_option(s["id"])]
    log.info("pv/option subcategories: %s", [s["id"] for s in pv_opt])
    log.info("skipping %d other subcategories", len(skipped))

    if not pv_opt:
        log.error("No pv/option subcategories found — aborting")
        sys.exit(1)

    stale = conn.execute(
        "SELECT COUNT(*) FROM download_log WHERE " + " OR ".join(f"subcategory_id LIKE '{p}%'" for p in PV_OPT_PREFIXES)
    ).fetchone()[0]
    log.info("download_log rows to clear: %d", stale)
    return brain, conn, pv_opt, stale


def clear_download_log(conn):
    conn.execute(
        "DELETE FROM download_log WHERE " + " OR ".join(f"subcategory_id LIKE '{p}%'" for p in PV_OPT_PREFIXES)
    )
    conn.commit()


def refresh_and_report(brain, conn, pv_opt):
    """Download every pv/option combo, stamp the metadata marker and log totals."""
    t0 = time.time()
    total = download_all_fields(brain, conn, pv_opt)

    fields = conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0]
    pv_fields = conn.execute("SELECT COUNT(*) FROM data_fields WHERE category_id IN ('pv','option')").fetchone()[0]
    conn.execute(
        "INSERT OR REPLACE INTO metadata VALUES (?,?)",
        ("last_pv_option_refresh", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())),
    )
    conn.commit()

    log.info("=" * 60)
    log.info(
        "Done in %.1f min — refreshed %d rows; data_fields now %d total, %d pv/option",
        (time.time() - t0) / 60,
        total,
        fields,
        pv_fields,
    )
    log.info("=" * 60)
    conn.close()
