"""refresh_priors aggregation: marginal cell, neutralization, NULL-template skip."""

from tests.test_f3_priors.conftest import mem_conn, seed_alpha


def test_refresh_priors_aggregates_by_marginal_cell():
    """refresh_priors groups by (template, region, universe, delay), counting hits at sharpe>=1.0."""
    from generator import cell_priors
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    # 3 alphas in (power_ratio, USA, TOP3000, 1): 1 hit, 2 miss.
    seed_alpha(conn, "a1", "power_ratio", "USA", "TOP3000", 1, 1.5)  # hit
    seed_alpha(conn, "a2", "power_ratio", "USA", "TOP3000", 1, 0.5)
    seed_alpha(conn, "a3", "power_ratio", "USA", "TOP3000", 1, 0.8)
    # 1 alpha in another cell: 0 hits.
    seed_alpha(conn, "b1", "raw_regression_long", "USA", "TOP3000", 1, 0.5)
    conn.commit()

    refresh_priors(conn)

    # Posterior mean: (1+hits) / (1+49+count). First cell: (1+1)/(50+3) = 2/53 ≈ 0.03774.
    expected = 2.0 / 53.0
    assert abs(cell_priors.hit_weight("power_ratio", "USA", "TOP3000", 1) - expected) < 1e-9
    # Second cell: (1+0)/(50+1) = 1/51 ≈ 0.01961.
    expected2 = 1.0 / 51.0
    assert abs(cell_priors.hit_weight("raw_regression_long", "USA", "TOP3000", 1) - expected2) < 1e-9


def test_refresh_priors_marginalizes_over_neutralization():
    """Two alphas in same (template, region, universe, delay) but different neutralization
    aggregate into one cell_priors row (marginal cell)."""
    from generator import cell_priors
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    # Same selection cell, different neutralization.
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, is_sharpe, status, template, pyramid_categories, created_at) "
        "VALUES ('a1', 's', 'e', 'USA', 'TOP3000', 1, 'MARKET', 1.5, 'X', 'power_ratio', '[\"pv\"]', 'd')"
    )
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, is_sharpe, status, template, pyramid_categories, created_at) "
        "VALUES ('a2', 's', 'e', 'USA', 'TOP3000', 1, 'SECTOR', 1.5, 'X', 'power_ratio', '[\"pv\"]', 'd')"
    )
    conn.commit()

    refresh_priors(conn)

    # 2 hits, 2 count -> (1+2)/(50+2) = 3/52.
    expected = 3.0 / 52.0
    assert abs(cell_priors.hit_weight("power_ratio", "USA", "TOP3000", 1) - expected) < 1e-9


def test_refresh_priors_ignores_unreachable_pyramids():
    """Alphas whose pyramid needs fundamental/model/news data cannot be
    reproduced by the pv/option generator, so their outcomes must not fit the
    priors (the same reachability rule the diversity weights use)."""
    from generator import cell_priors
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    seed_alpha(conn, "a1", "power_ratio", "USA", "TOP3000", 1, 1.5)  # reachable hit
    seed_alpha(conn, "a2", "power_ratio", "USA", "TOP3000", 1, 5.0, pyramid_categories='["fundamental"]')
    seed_alpha(conn, "a3", "power_ratio", "USA", "TOP3000", 1, 5.0, pyramid_categories=None)
    conn.commit()

    refresh_priors(conn)

    # 1 hit, 1 count → (1+1)/(50+1) = 2/51.
    expected = 2.0 / 51.0
    assert abs(cell_priors.hit_weight("power_ratio", "USA", "TOP3000", 1) - expected) < 1e-9


# The NULL-template skip lives in `test_refresh_null_template.py`.
