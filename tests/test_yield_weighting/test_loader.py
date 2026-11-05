"""load_diversity_weights populates region_config_yield_weights from alpha_results."""

import generator.diversity_weights as dw
from tests.test_yield_weighting.conftest import make_yield_db


def test_load_populates_yield_weights():
    conn = make_yield_db()
    fresh = dw.DiversityCache()
    dw.set_state(fresh)
    try:
        dw.load_diversity_weights(conn)
        ind_w = fresh.region_config_yield_weights[("IND", "TOP500", 1)]
        usa_w = fresh.region_config_yield_weights[("USA", "TOP3000", 1)]
        # IND has 6x the win rate; with same sample size, posterior mean is much higher.
        assert ind_w > usa_w
        # IND = (1+12)/(50+100) = 13/150.
        assert abs(ind_w - 13 / 150) < 1e-9
        # USA = (1+2)/(50+100) = 3/150.
        assert abs(usa_w - 3 / 150) < 1e-9
    finally:
        dw.set_state(dw.DiversityCache())


def test_unreachable_alphas_do_not_move_the_posterior():
    """An alpha whose pyramid needs out-of-scope data cannot be reproduced by
    the pv/option generator, so its outcome must not be counted."""
    conn = make_yield_db()
    # Perfect (but unreachable) alphas must leave every weight unchanged.
    conn.executemany(
        "INSERT INTO alpha_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("MARKET", 4, 0.08, "USA", "TOP3000", 1, 9.9, None, '["fundamental"]'),
            ("MARKET", 4, 0.08, "USA", "TOP3000", 1, 9.9, None, None),
        ],
    )
    conn.commit()
    fresh = dw.DiversityCache()
    dw.set_state(fresh)
    try:
        dw.load_diversity_weights(conn)
        assert abs(fresh.region_config_yield_weights[("USA", "TOP3000", 1)] - 3 / 150) < 1e-9
        assert abs(fresh.region_config_yield_weights[("IND", "TOP500", 1)] - 13 / 150) < 1e-9
    finally:
        dw.set_state(dw.DiversityCache())
