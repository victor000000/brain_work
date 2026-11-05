"""Tests for P6 F3 + pyramid integration — expected_multiplier computation.

The `_alpha_max_multiplier` unit tests live in `tests/test_f3_multiplier.py`.
"""

import time

from core.db import connect, init_tables


def _mem_conn():
    conn = connect(":memory:")
    init_tables(conn)
    return conn


def test_refresh_priors_writes_expected_multiplier():
    """End-to-end: 2 alphas in a cell → expected_multiplier averages their
    cap-adjusted max-multipliers."""
    from generator import cell_priors
    from generator.priors_loader import refresh_priors

    conn = _mem_conn()
    now = int(time.time())
    # Seed pyramid_multipliers: pv=1.4, option=1.7 in (USA, 1). Categories must
    # be reachable (pv/option) — priors fitting skips the rest.
    conn.executemany(
        "INSERT INTO pyramid_multipliers VALUES (?, ?, ?, ?, ?)",
        [("pv", "USA", 1, 1.4, now), ("option", "USA", 1, 1.7, now)],
    )
    # Seed pyramid_alpha_counts at 0 for both (no saturation).
    conn.executemany(
        "INSERT INTO pyramid_alpha_counts VALUES (?, ?, ?, ?, ?)",
        [("pv", "USA", 1, 0, now), ("option", "USA", 1, 0, now)],
    )
    # Two alphas in (power_ratio, USA, TOP3000, 1):
    #   a1 has cats ["pv"]          → max-mult = 1.4
    #   a2 has cats ["pv","option"] → max-mult = 1.7
    # Cell average = (1.4 + 1.7) / 2 = 1.55
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, is_sharpe, status, template, pyramid_categories, created_at) "
        "VALUES ('a1','s','e','USA','TOP3000',1,'MARKET',0.5,'UNSUBMITTED','power_ratio','[\"pv\"]','d')"
    )
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, is_sharpe, status, template, pyramid_categories, created_at) "
        "VALUES ('a2','s','e','USA','TOP3000',1,'SECTOR',0.5,'UNSUBMITTED','power_ratio','[\"pv\",\"option\"]','d')"
    )
    conn.commit()

    refresh_priors(conn)

    em = cell_priors.expected_multiplier("power_ratio", "USA", "TOP3000", 1)
    assert abs(em - 1.55) < 1e-9


def test_expected_multiplier_falls_back_to_1_for_cell_with_no_resolvable_alphas():
    """A cell whose historical alphas have NULL/unknown pyramid_categories
    keeps the default expected_multiplier=1.0."""
    from generator import cell_priors
    from generator.priors_loader import refresh_priors

    conn = _mem_conn()
    # Seed an alpha but no pyramid_multipliers/pyramid_alpha_counts: max-mult is None.
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, is_sharpe, status, template, pyramid_categories, created_at) "
        "VALUES ('a1','s','e','USA','TOP3000',1,'MARKET',0.5,'UNSUBMITTED','t1','[\"pv\"]','d')"
    )
    conn.commit()

    refresh_priors(conn)

    # Cell exists in cell_priors (from F3 logic) but expected_multiplier is the
    # default 1.0 because no alpha contributed a non-None max-multiplier.
    em = cell_priors.expected_multiplier("t1", "USA", "TOP3000", 1)
    assert em == 1.0
