"""High-performance templates derived from top-performer analysis.

regression_pair (68% submit rate): raw ts_regression at long windows, no zscore wrap.
power_spread (16% submit rate): signed_power of field ratio.
"""

import random

# 189 dropped 2026-04-26: hit rate 1.61% (n=620) vs 2.18% (126) and 1.96% (252).
# z = -1.7 against canonical baseline 2.74%. See investigation in conversation log.
W_LONG = [126, 252]
W_MED = [42, 63, 126]
POWERS = [0.25, 0.3, 0.5]


def raw_regression_long(f1, f2):
    """Raw regression at yearly window — regression_pair pattern (68% submit rate)."""
    w = random.choice(W_LONG)
    return f"rank(ts_regression({f1}, {f2}, {w}))"


def raw_regression_medium(f1, f2):
    """Raw regression at quarterly windows."""
    w = random.choice(W_MED)
    return f"rank(ts_regression({f1}, {f2}, {w}))"


def power_ratio(f1, f2):
    """Power-dampened ratio with a denominator-scaled regularizer.

    A bare 0.01 cannot be added to a price or share count. Its rolling
    absolute mean supplies the denominator's units and a relative scale.
    An entirely zero history remains undefined rather than inventing a value.
    """
    p = random.choice(POWERS)
    return f"rank(signed_power({f1} / ({f2} + 0.01 * ts_mean(abs({f2}), 20)), {p}))"
