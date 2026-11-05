"""Canonical alpha patterns ported from cnhkmcp 3.1.11 KB.

Each template mirrors a SIMULATION_EXAMPLE entry in cnhkmcp's knowledge base,
generalized into a 2-field signature so it can be sampled by the explorer.
These are exploration additions — they start with default diversity weight
(1/(1+0)=1.0) and converge to their empirical hit rate as observations land.
"""

import random


def quantile_ts_rank(f1, _f2):
    """quantile(ts_rank(field, w)) — normalized fundamental rank.
    Source: pretax_income example (USA/TOP3000/d1, MARKET).
    """
    w = random.choice([126, 250, 504])
    return f"quantile(ts_rank({f1},{w}))"


def group_rank_diff(f1, f2):
    """group_rank(f1, sector) - group_rank(f2, sector) — within-group spread.
    Source: sales-growth example (USA/TOP3000/d1, MARKET).
    """
    group = random.choice(["sector", "industry", "subindustry"])
    return f"group_rank({f1},{group}) - group_rank({f2},{group})"


def ts_corr_long(f1, f2):
    """-ts_corr(ts_backfill(f1, w1), ts_backfill(f2, w1), w2) — long-window correlation.
    Source: fscore_momentum/value example (USA/TOP200/d1, INDUSTRY).
    """
    w1 = random.choice([66, 132])
    w2 = random.choice([504, 756])
    return f"-ts_corr(ts_backfill({f1},{w1}),ts_backfill({f2},{w1}),{w2})"


def trade_when_event(f1, f2):
    """trade_when(days_from_last_change(f2)<=5, rank(f1), -1) — event-driven alpha.
    Source: EPS-surprise example (USA/TOP3000/d1, INDUSTRY).
    """
    return f"trade_when(days_from_last_change({f2})<=5, rank({f1}), -1)"


def ts_backfill_negmean(f1, _f2):
    """-ts_mean(ts_backfill(f1, 252), 504) — backfilled mean-reverting long signal.
    Source: pv13_ustomergraphrank_hub_rank example (USA/TOP1000/d1, INDUSTRY).
    """
    inner_w = random.choice([126, 252])
    outer_w = random.choice([252, 504])
    return f"-ts_mean(ts_backfill({f1},{inner_w}),{outer_w})"
