"""Detect subcategories whose API datasetCount is greater than the cached value."""

from core.db import connect
from download.session import API_BASE
from tools.apply_discovery_and_redownload._config import DB_PATH
from tools.apply_discovery_and_redownload._log import log


def grown_subcats(brain):
    """Return list of subcategory_ids whose API datasetCount exceeds the cache."""
    resp = brain.get(f"{API_BASE}/data-categories")
    if resp.status_code != 200:
        log.warning("data-categories failed: %d", resp.status_code)
        return []
    cats = resp.json()
    api_counts = {ch["id"]: ch.get("datasetCount", 0) or 0 for cat in cats for ch in cat.get("children", [])}
    conn = connect(DB_PATH)
    cached = {
        r[0]: r[1] or 0
        for r in conn.execute("SELECT id, dataset_count FROM dataset_categories WHERE parent_id IS NOT NULL")
    }
    conn.close()
    return [sid for sid, n in api_counts.items() if n > cached.get(sid, 0)]
