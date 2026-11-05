"""Pick `count` fields with at least 1 from the target pyramid category.

For 1-field picks: choose a target-category field directly.
For 2+: lock in a target-category field, then fill the rest using the
same-dataset bias from a different dataset (90% same-dataset for the
remaining slots if count >= 2; cross-dataset 10% of the time).
"""

import random


def pick_with_target(pool, datasets_by_category, target, count):
    """Return `count` field IDs guaranteeing at least 1 from the target category."""
    target_datasets = [ds for ds in datasets_by_category.get(target, []) if pool.get(ds)]
    if not target_datasets:
        return None

    target_ds = random.choice(target_datasets)
    target_pool = pool[target_ds]

    if count == 1:
        return [random.choice(target_pool)]

    # Pick `count` fields from the same target dataset when possible — that
    # gives the unit-safety property AND keeps the alpha in the target pyramid.
    if len(target_pool) >= count and random.random() < 0.9:
        return random.sample(target_pool, count)

    # Otherwise: 1 anchor field from target, fill the rest with cross-dataset.
    chosen = [random.choice(target_pool)]
    other_dataset_ids = [d for d in pool if d != target_ds]
    if not other_dataset_ids:
        return chosen if len(chosen) == count else None
    used = {target_ds}
    for _ in range((count - 1) * 10):
        if len(chosen) >= count:
            break
        ds = random.choice(other_dataset_ids)
        if ds in used and len(other_dataset_ids) > count - 1:
            continue
        chosen.append(random.choice(pool[ds]))
        used.add(ds)
    return chosen if len(chosen) == count else None
