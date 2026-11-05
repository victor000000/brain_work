"""Top-level pick_matrix — dispatches between target / same-dataset / cross-dataset."""

import random

import generator.field_picker as fp
from generator.field_picker_matrix.strategies import pick_cross_dataset, pick_same_dataset
from generator.field_picker_matrix.target import get_target_category
from generator.field_picker_matrix.with_target import pick_with_target


def pick_matrix(count=2):
    """Pick count MATRIX fields.

    If a target_category is set, ensures at least 1 field comes from that
    category (so the resulting alpha lands in the target pyramid). Falls
    back to legacy 90% same-dataset / 10% cross-dataset when no target is
    set, the target's category has no available fields, or count == 0.
    """
    cache = fp.get_cache()
    pool = cache.matrix_by_dataset
    dataset_ids = list(pool.keys())
    if not dataset_ids:
        return []

    target = get_target_category()
    if target and target in cache.datasets_by_category:
        result = pick_with_target(pool, cache.datasets_by_category, target, count)
        if result and len(result) == count:
            return result
        # Target unsatisfiable (rare) — fall through to legacy behavior.

    if random.random() < 0.9:
        result = pick_same_dataset(pool, dataset_ids, count)
        if result:
            return result

    result = pick_cross_dataset(pool, dataset_ids, count)
    if result:
        return result

    # A single-dataset pool can't satisfy pick_cross_dataset, which returns []
    # for len(dataset_ids) < 2. Fall back rather than hand back an empty pick —
    # this is what made MEA/TOP300/d1 (2 fields, one dataset) flake.
    return pick_same_dataset(pool, dataset_ids, count) or []
