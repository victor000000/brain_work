"""Yield-based weights — Beta-Bernoulli posterior expected hit rate.

Used when BRAIN_YIELD_WEIGHTING is set; configs with <50 sims are dominated
by the prior, configs with >>50 sims converge to their empirical hit rate.

Like the count weights in `compute_count`, only reachable (pv/option) alphas
are counted: an unreachable alpha's outcome cannot be reproduced by the
generator, so it must not move the posterior.
"""

from generator.diversity_weights.compute_count import _REACHABLE_SQL as REACHABLE_SQL

# Beta-Bernoulli prior: mean = 1/50 = 2% (matches observed baseline hit rate).
YIELD_PRIOR_ALPHA = 1.0
YIELD_PRIOR_BETA = 49.0
YIELD_HIT_THRESHOLD = 1.0  # is_sharpe >= 1.0 counts as a "winner"


def yield_weight(winners: int, count: int, alpha: float = YIELD_PRIOR_ALPHA, beta: float = YIELD_PRIOR_BETA) -> float:
    """Posterior mean of a Beta-Bernoulli model: (a + winners) / (a + b + count)."""
    return (alpha + winners) / (alpha + beta + count)


YIELD_PRIOR_MEAN = yield_weight(0, 0)


def compute_config_yield_weights(conn):
    """Per-config Beta-Bernoulli posterior expected hit rate."""
    rows = conn.execute(
        "SELECT region, universe, delay, COUNT(*), "
        "SUM(CASE WHEN is_sharpe >= ? THEN 1 ELSE 0 END) "
        f"FROM alpha_results WHERE {REACHABLE_SQL} GROUP BY region, universe, delay",
        (YIELD_HIT_THRESHOLD,),
    ).fetchall()
    return {
        (region, universe, delay): yield_weight(winners or 0, count) for region, universe, delay, count, winners in rows
    }
