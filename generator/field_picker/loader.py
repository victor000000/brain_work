"""Load MATRIX, VECTOR, and GROUP field pools into the FieldCache singleton.

No universe fallback: with the canonical OPTIONS-derived REGION_CONFIGS
every (region, universe, delay) entry has real fields, and the explorer's
pyramid3 picker only proposes valid combos. If a universe happens to be
sparse, the caller (random_generator.generate_expressions) handles the
empty-pool case gracefully and just returns no expressions for that batch.
"""

from core.log import get_file_logger
from generator.field_picker.cache import get_cache
from generator.field_queries import query_group_fields, query_vector_fields
from generator.field_queries_matrix import query_matrix_fields

glog = get_file_logger("generator")


def load_all_fields(conn, region, delay, universe):
    """Load MATRIX, VECTOR, and GROUP field pools for the requested combo.

    Cached per (region, delay, universe) — repeated calls are no-ops until
    one of those changes.

    The cache marker is set only after every loader returns. Setting it up
    front cached a partial or empty pool for the process lifetime whenever a
    query failed mid-load: the next call saw the key and skipped the retry.
    """
    cache = get_cache()
    cache_key = (region, delay, universe)
    if cache_key == cache.last_loaded:
        return

    matrix_by_dataset, dataset_to_category = query_matrix_fields(
        conn,
        region,
        delay,
        universe,
    )
    vector_fields = query_vector_fields(conn, region, delay, universe)
    group_fields = query_group_fields(conn, region, delay, universe)

    cache.matrix_by_dataset = matrix_by_dataset
    cache.dataset_to_category = dataset_to_category
    cache.rebuild_category_index()
    cache.vector_fields = vector_fields
    cache.group_fields = group_fields
    cache.last_loaded = cache_key

    glog.debug(
        "Loaded %s/%s/d%d: %d matrix_ds, %d cats, %d vec, %d grp",
        region,
        universe,
        delay,
        len(cache.matrix_by_dataset),
        len(cache.datasets_by_category),
        len(cache.vector_fields),
        len(cache.group_fields),
    )
