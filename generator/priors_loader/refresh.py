"""Top-level refresh_priors — recompute cell_priors and apply Tier-2 quarantine."""

import time

from core.log import get_file_logger
from generator import cell_priors
from generator.priors_loader._constants import _ALPHA, _BETA, _OOS_ALPHA, _OOS_BETA
from generator.priors_loader.aggregate import (
    accumulate_pyramid_multipliers,
    fetch_cell_counts,
    fetch_existing_quarantined_at,
    fetch_marginal_outcomes,
    fetch_oos_robustness_counts,
)
from generator.priors_loader.pyramid_lookups import load_pyramid_lookups
from generator.priors_loader.quarantine import decide

plog = get_file_logger("generator")


def _row_for_cell(cell, cnt, hits, outcomes, existing_q, now, cell_mult_sum, cell_mult_n, oos_counts):
    """Build the upsert tuple for one (template, region, universe, delay)."""
    template, region, universe, delay = cell
    hit_weight = (_ALPHA + hits) / (_ALPHA + _BETA + cnt)
    submitted, rejected = outcomes.get(cell, (0, 0))
    quarantined, quarantined_at = decide(
        rejected,
        submitted,
        hit_weight,
        existing_q.get(cell),
        now,
    )
    n_contrib = cell_mult_n.get(cell, 0)
    expected_multiplier = (cell_mult_sum[cell] / n_contrib) if n_contrib > 0 else 1.0
    n_with_test, n_robust = oos_counts.get(cell, (0, 0))
    oos_robustness = (_OOS_ALPHA + n_robust) / (_OOS_ALPHA + _OOS_BETA + n_with_test)
    return (
        template,
        region,
        universe,
        delay,
        cnt,
        hits,
        hit_weight,
        expected_multiplier,
        oos_robustness,
        quarantined,
        quarantined_at,
        now,
    )


def refresh_priors(conn) -> None:
    """Recompute cell_priors and apply Tier-2 quarantine + pyramid bias + OOS robustness."""
    rows = fetch_cell_counts(conn)
    outcomes = fetch_marginal_outcomes(conn)
    existing_q = fetch_existing_quarantined_at(conn)

    mults, counts = load_pyramid_lookups(conn)
    cell_mult_sum, cell_mult_n = accumulate_pyramid_multipliers(conn, mults, counts)
    oos_counts = fetch_oos_robustness_counts(conn)

    now = int(time.time())
    upserts = [
        _row_for_cell(
            (template, region, universe, delay),
            cnt,
            hits or 0,
            outcomes,
            existing_q,
            now,
            cell_mult_sum,
            cell_mult_n,
            oos_counts,
        )
        for template, region, universe, delay, cnt, hits in rows
    ]

    with conn:
        conn.execute("DELETE FROM cell_priors")
        conn.executemany(
            """
            INSERT INTO cell_priors
            (template, region, universe, delay, count, hits, hit_weight,
             expected_multiplier, oos_robustness, quarantined, quarantined_at, refreshed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            upserts,
        )

    cell_priors.load_priors(conn)
    plog.debug(
        "refresh_priors: %d cells, %d quarantined, t=%d",
        len(upserts),
        sum(1 for u in upserts if u[9] == 1),
        now,
    )
