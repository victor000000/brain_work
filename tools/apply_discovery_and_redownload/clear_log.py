"""Clear stale download_log rows so the next download fetches them fresh."""

from core.db import connect
from tools.apply_discovery_and_redownload._config import DB_PATH
from tools.apply_discovery_and_redownload._log import log


def clear_stale_download_log(grown_subcat_ids, new_combos):
    """Delete rows for grown subcategories and new (region, universe, delay) tuples."""
    conn = connect(DB_PATH)
    cleared = 0
    try:
        # DuckDB's rowcount is -1 for DELETE, so count what RETURNING yields.
        for sid in grown_subcat_ids:
            cur = conn.execute("DELETE FROM download_log WHERE subcategory_id = ? RETURNING 1", (sid,))
            cleared += len(cur.fetchall())
        for region, universe, delay in new_combos:
            cur = conn.execute(
                "DELETE FROM download_log WHERE region=? AND universe=? AND delay=? RETURNING 1",
                (region, universe, delay),
            )
            cleared += len(cur.fetchall())
        conn.commit()
    finally:
        conn.close()
    log.info("Cleared %d stale download_log rows", cleared)
