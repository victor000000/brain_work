"""Unsubmitted PV-only example for static Python probe validation.

No data or SDK calls execute during the static validation tests.
"""

import numpy as np
from brain.alphas import alpha


def tied_rank(values):
    """Finite inputs receive average ranks scaled to [0, 1]."""
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2
        start = end
    return ranks / (len(values) - 1)


@alpha(data=["returns"], store=[])
def pca_residual_reversal(data, store):
    """Return NaN for insufficient history, missing inputs or degenerate scores."""
    panel = np.asarray(data.returns, dtype=np.float64)
    output = np.full(panel.shape[1], np.nan, dtype=np.float32)
    if panel.shape[0] < 60:
        return output
    panel = panel[-60:]
    # Complete history is intentional: missing returns are never zero-filled.
    eligible = (data.universe[-1] == 1) & np.all(np.isfinite(panel), axis=0)
    columns = np.flatnonzero(eligible)
    if len(columns) < 5:
        return output
    centered = panel[:, columns] - panel[:, columns].mean(axis=0)
    _, singular, right = np.linalg.svd(centered, full_matrices=False)
    tolerance = np.finfo(np.float64).eps * max(centered.shape) * singular[0]
    if np.count_nonzero(singular > tolerance) <= 3:
        return output
    factors = right[:3]
    residual = centered - (centered @ factors.T) @ factors
    cumulative = np.vstack((np.zeros((1, len(columns))), np.cumsum(residual, axis=0)))
    rolling = cumulative[10:] - cumulative[:-10]
    deviation = rolling.std(axis=0)
    scale = np.max(np.abs(rolling), axis=0)
    valid = np.isfinite(deviation) & (deviation > np.finfo(np.float64).eps * scale)
    if np.count_nonzero(valid) < 2:
        return output
    score = (rolling[-1, valid] - rolling[:, valid].mean(axis=0)) / deviation[valid]
    finite = np.isfinite(score)
    if np.count_nonzero(finite) < 2:
        return output
    output[columns[valid][finite]] = (0.5 - tied_rank(score[finite])).astype(np.float32)
    return output
