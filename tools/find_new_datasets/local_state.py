"""Read local brain_data.duckdb state needed for the diff."""

from core.db import connect
from tools.find_new_datasets._config import DB_PATH


def load_local_state():
    """Return (known_dataset_ids, cached_subcat_counts).

    known_dataset_ids:    set of distinct dataset.id values already stored.
    cached_subcat_counts: dict[subcat_id] -> (count, name) from dataset_categories.
    """
    conn = connect(DB_PATH)
    try:
        known_dataset_ids = {r[0] for r in conn.execute("SELECT DISTINCT id FROM datasets WHERE id != ''")}
        cached_subcat_counts = {
            r[0]: (r[1] or 0, r[2] or "")
            for r in conn.execute("SELECT id, dataset_count, name FROM dataset_categories WHERE parent_id IS NOT NULL")
        }
    finally:
        conn.close()
    return known_dataset_ids, cached_subcat_counts
