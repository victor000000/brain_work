"""refresh_priors must skip alphas with no template.

Split out of `tests/test_f3_priors/test_refresh.py`.
"""

from tests.test_f3_priors.conftest import mem_conn, seed_alpha


def test_refresh_priors_skips_null_template():
    """alpha_results rows with NULL template are excluded (pre-backfill rows)."""
    from generator import cell_priors
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    seed_alpha(conn, "a1", "power_ratio", "USA", "TOP3000", 1, 1.5)
    # Reachable pyramid, but NULL template: template must be the only reason
    # the orphan is skipped.
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " is_sharpe, status, pyramid_categories, created_at) "
        "VALUES ('orphan', 'sim', 'expr', 'USA', 'TOP3000', 1, 5.0, 'UNSUBMITTED', '[\"pv\"]', 'd')"
    )
    conn.commit()

    refresh_priors(conn)

    # Only 'power_ratio' cell exists; orphan row is ignored.
    n = conn.execute("SELECT COUNT(*) FROM cell_priors").fetchone()[0]
    assert n == 1
    # And the prior reflects ONLY the templated row.
    expected = 2.0 / 51.0  # 1 hit, 1 count.
    assert abs(cell_priors.hit_weight("power_ratio", "USA", "TOP3000", 1) - expected) < 1e-9
