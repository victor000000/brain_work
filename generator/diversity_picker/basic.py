"""General-purpose inverse-coverage value picker."""

import random


def weighted_pick(values, weights_dict):
    """Pick a value weighted by inverse coverage.

    `weights_dict` maps value -> weight (typically 1/(1+count)). Missing
    values default to weight=1.0. Returns None when `values` is empty.
    """
    if not values:
        return None
    value_weights = [weights_dict.get(value, 1.0) for value in values]
    total = sum(value_weights)
    rand_val = random.random() * total
    cumulative = 0
    for i, value in enumerate(values):
        cumulative += value_weights[i]
        if rand_val <= cumulative:
            return value
    return values[-1]
