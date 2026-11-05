"""SQL query for loading MATRIX data fields.

MATRIX fields are the primary input to alpha expressions.
Grouped by dataset to support same-dataset field picking (unit safety).

Exclusions: non-price/option categories, identifier fields. The field_blacklist
table is not consulted. See field_queries.py for full exclusion documentation.

The cap is **per dataset**, not global. A single `LIMIT 500` ordered by coverage
let a large dataset crowd out every smaller one: pv holds ~88k fields against
option's 619, and the highest-coverage pv field outranks any option field, so
the pool contained only pv while the restriction is pv *and* option. Ranking
within each dataset guarantees every one is represented.
"""

from core.log import get_file_logger
from generator.field_dead import cached_dead_fields
from generator.field_queries import CATEGORY_FILTER, COVERAGE_OK, identifier_filter, not_label_filter

flog = get_file_logger("fields")

# Fields kept per dataset. Sized so the total stays in the same order as the
# old global cap even when many datasets are present.
PER_DATASET_LIMIT = 60


def query_matrix_fields(conn, region, delay, universe):
    """Load MATRIX fields grouped by dataset, with dataset->category map.

    Returns (fields_by_dataset, dataset_to_category):
      fields_by_dataset:    dict[dataset_id] -> list[field_id]
      dataset_to_category:  dict[dataset_id] -> category_id

    Prefers high coverage *within* each dataset. category_id is needed for
    pyramid-3+ picking (see pick_matrix), since each BRAIN pyramid is keyed by
    category.
    """
    rows = conn.execute(
        f"""
        SELECT id, dataset_id, category_id FROM (
            SELECT id, dataset_id, category_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY dataset_id
                       ORDER BY coverage DESC, RANDOM()
                   ) AS rn
            FROM data_fields
            WHERE region=? AND delay=? AND universe=? AND type='MATRIX'
              AND {COVERAGE_OK} AND date_coverage >= 0.5
              AND {identifier_filter()}
              {not_label_filter()}
              {CATEGORY_FILTER}
        )
        WHERE rn <= {PER_DATASET_LIMIT}
    """,
        (region, delay, universe),
    ).fetchall()
    # Fields the platform has never once simulated into an alpha, from our own
    # recorded outcomes (`generator/field_dead.py`). Dropped here rather than in
    # the SQL because the evidence lives in `simulations`, not `data_fields`.
    dead = cached_dead_fields(conn)
    fields_by_dataset = {}
    dataset_to_category = {}
    dropped = 0
    for field_id, dataset_id, category_id in rows:
        if field_id in dead:
            dropped += 1
            continue
        fields_by_dataset.setdefault(dataset_id, []).append(field_id)
        if dataset_id not in dataset_to_category:
            dataset_to_category[dataset_id] = category_id
    if dropped:
        flog.debug("MATRIX %s/%s/d%d: %d dead fields dropped", region, universe, delay, dropped)
    total = sum(len(v) for v in fields_by_dataset.values())
    n_cats = len(set(dataset_to_category.values()))
    flog.debug(
        "MATRIX %s/%s/d%d: %d fields, %d datasets, %d categories",
        region,
        universe,
        delay,
        total,
        len(fields_by_dataset),
        n_cats,
    )
    return fields_by_dataset, dataset_to_category
