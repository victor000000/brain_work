"""Pull alpha-side aggregates needed for cell_priors recompute.

Only alphas the generator can still produce are counted: an alpha whose
`pyramid_categories` include fundamental, model or news data is unreachable
under the pv/option restriction, and fitting cell priors on that population
steers generation with outcomes it can never reproduce. The predicate is
imported from `diversity_weights.compute_count` so the two weight paths cannot
drift apart.
"""

import json

from generator.diversity_weights.compute_count import _REACHABLE_SQL as REACHABLE_SQL
from generator.priors_loader._constants import _OOS_RATIO_THRESHOLD
from generator.priors_loader.pyramid_lookups import alpha_max_multiplier


def fetch_cell_counts(conn):
    """Per-cell (template, region, universe, delay) count + hit count."""
    return conn.execute(
        f"""
        SELECT template, region, universe, delay,
               COUNT(*) AS cnt,
               SUM(CASE WHEN is_sharpe >= 1.0 THEN 1 ELSE 0 END) AS hits
        FROM alpha_results
        WHERE template IS NOT NULL AND {REACHABLE_SQL}
        GROUP BY template, region, universe, delay
        """
    ).fetchall()


def fetch_marginal_outcomes(conn):
    """Per-cell submission_outcomes summed over neutralization."""
    rows = conn.execute(
        """
        SELECT template, region, universe, delay,
               SUM(submitted), SUM(rejected), SUM(throttled)
        FROM submission_outcomes
        GROUP BY template, region, universe, delay
        """
    ).fetchall()
    return {(t, r, u, d): (s or 0, j or 0) for t, r, u, d, s, j, _th in rows}


def fetch_existing_quarantined_at(conn):
    """{cell -> quarantined_at} for the prior pass; used by lift-window logic."""
    return {
        (t, r, u, d): qa
        for t, r, u, d, qa in conn.execute("SELECT template, region, universe, delay, quarantined_at FROM cell_priors")
    }


def fetch_oos_robustness_counts(conn):
    """Per-cell (n_with_test, n_robust) for OOS-robustness posterior.

    n_with_test: count of alphas with is_sharpe > 0 AND test_sharpe IS NOT NULL.
    n_robust: subset where test_sharpe > _OOS_RATIO_THRESHOLD * is_sharpe.
    """
    rows = conn.execute(
        f"""
        SELECT template, region, universe, delay,
               SUM(CASE WHEN test_sharpe IS NOT NULL AND is_sharpe > 0 THEN 1 ELSE 0 END),
               SUM(CASE WHEN test_sharpe IS NOT NULL AND is_sharpe > 0
                         AND test_sharpe > {_OOS_RATIO_THRESHOLD} * is_sharpe THEN 1 ELSE 0 END)
        FROM alpha_results
        WHERE template IS NOT NULL AND {REACHABLE_SQL}
        GROUP BY template, region, universe, delay
        """
    ).fetchall()
    return {(t, r, u, d): (n_test or 0, n_robust or 0) for t, r, u, d, n_test, n_robust in rows}


def accumulate_pyramid_multipliers(conn, mults, counts):
    """Per-cell average of `alpha_max_multiplier` over its historical alphas.

    Returns (cell_mult_sum, cell_mult_n) — divide one by the other to get the
    per-cell expected_multiplier. Cells with no contributing alpha are absent
    from both dicts; caller defaults to 1.0.
    """
    cell_mult_sum: dict[tuple, float] = {}
    cell_mult_n: dict[tuple, int] = {}
    for tmpl, region, universe, delay, pyr_json in conn.execute(
        "SELECT template, region, universe, delay, pyramid_categories "
        f"FROM alpha_results "
        f"WHERE template IS NOT NULL AND {REACHABLE_SQL}"
    ):
        cats = json.loads(pyr_json)
        m = alpha_max_multiplier(cats, region, delay, mults, counts)
        if m is None:
            continue
        key = (tmpl, region, universe, delay)
        cell_mult_sum[key] = cell_mult_sum.get(key, 0.0) + m
        cell_mult_n[key] = cell_mult_n.get(key, 0) + 1
    return cell_mult_sum, cell_mult_n
