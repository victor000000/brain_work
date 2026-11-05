"""Same-dataset and cross-dataset pick strategies (no target).

These are the historical 90/10 fallback used when no target category is set,
or when the target's category has no available fields.
"""

import random


def pick_same_dataset(pool, dataset_ids, count):
    """Pick fields from a single dataset (prevents unit mismatch)."""
    big_ds = [d for d in dataset_ids if len(pool[d]) >= count]
    if not big_ds:
        return None
    ds = random.choice(big_ds)
    return random.sample(pool[ds], count)


def pick_cross_dataset(pool, dataset_ids, count):
    """Pick fields across different datasets (more diversity)."""
    if len(dataset_ids) < 2:
        return []
    chosen_fields, used_datasets = [], set()
    for _ in range(count * 10):
        if len(chosen_fields) >= count:
            break
        dataset = random.choice(dataset_ids)
        if dataset in used_datasets and len(dataset_ids) > count:
            continue
        chosen_fields.append(random.choice(pool[dataset]))
        used_datasets.add(dataset)
    return chosen_fields
