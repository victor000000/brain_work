"""cnhkmcp advanced template: cross-sectional rank-zscore with field interaction."""

import random

W = [10, 21, 42, 63]


def scale_rank_zscore(f1, f2):
    """cnhkmcp: scale(rank(ts_zscore(f, d)))."""
    w = random.choice(W)
    return f"rank(scale(rank(ts_zscore({f1},{w}))) * rank({f2}))"
