"""Re-rank the check queue by what a submission needs, not by sharpe alone.

Split out of `checker/auto_check_queue.py`, which calls `by_expected_value`.

Sharpe is not the quantity that decides a submission. Correlation is, and it
varies enormously by shape: on 2026-10-07 `sector_neutralized` and
`vol_adjusted_signal` were 7.7% of generation and **96%** of the
self-correlation failures, while `ts_backfill_negmean`, `staleness_decay`,
`scale_rank_zscore` and `power_ratio` had never failed correlation at all
across 495 checked candidates.

That matters because a run's 1200s budget covers only 20-36 of the 60
candidates it asks for, so the order decides which shapes ever get looked at.
`corr_prior` already measures the weight for the *generator*; the same number
belongs here, where the run budget is spent.
"""

from generator import corr_prior

# How many times the batch size to fetch before re-ranking. The window has to be
# wider than the batch, or the re-rank could only shuffle the alphas the sharpe
# order had already chosen.
RERANK_WINDOW = 3


def by_expected_value(rows, limit):
    """`[(alpha_id, sharpe)]`, best expected value first.

    `rows` are `(alpha_id, sharpe, template, deferred, region, universe, delay)`
    from the selection query,
    already in SQL order (deferred last, best sharpe first). The sort keeps
    deferred alphas last — that ordering is what stops an undecidable alpha
    heading every run — and reorders the rest by `sharpe x correlation weight`.

    With no weights loaded every factor is 1.0 and the order is exactly what the
    SQL returned, so a cold cache degrades to the old behaviour rather than to
    something arbitrary.
    """
    ranked = sorted(rows, key=lambda r: (r[3], -(r[1] * corr_prior.corr_weight(r[2] or "", cell=(r[4], r[5], r[6])))))
    return [(r[0], r[1]) for r in ranked[:limit]]
