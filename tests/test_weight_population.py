"""Weight maps must be fitted on alphas the generator can still produce.

163,981 of 179,377 stored alphas involve model/analyst/fundamental/news data.
Restricting generation to pv/option without restricting the weights leaves the
generator steered by a population that is 91% unreachable.
"""

import pytest

from core.db import connect
from generator.diversity_weights.compute_count import (
    compute_config_weights,
    compute_test_period_weights,
    compute_weights,
)


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.execute("""
        CREATE TABLE alpha_results (
            alpha_id TEXT, region TEXT, universe TEXT, delay INTEGER,
            decay INTEGER, pyramid_categories TEXT, raw_json TEXT
        )
    """)
    rows = [
        ("a1", "USA", "TOP3000", 1, 4, '["pv"]', '{"settings":{"testPeriod":"P1Y"}}'),
        ("a2", "USA", "TOP3000", 1, 4, '["option"]', '{"settings":{"testPeriod":"P1Y"}}'),
        ("a3", "USA", "TOP3000", 1, 8, '["pv","option"]', '{"settings":{"testPeriod":"P1Y"}}'),
        # excluded population
        ("a4", "USA", "TOP3000", 1, 8, '["model"]', '{"settings":{"testPeriod":"P0Y6M"}}'),
        ("a5", "CHN", "TOP2000U", 0, 4, '["analyst","model"]', '{"settings":{"testPeriod":"P0Y6M"}}'),
        ("a6", "CHN", "TOP2000U", 0, 4, '["fundamental"]', '{"settings":{"testPeriod":"P0Y6M"}}'),
    ]
    c.executemany("INSERT INTO alpha_results VALUES (?,?,?,?,?,?,?)", rows)
    c.commit()
    return c


def test_decay_weights_count_only_reachable_alphas(conn):
    """decay=8 has two alphas — a3 (pv+option, reachable) and a4 (model, not).

    Filtered it counts once, so its inverse-coverage weight rises from 1/3
    (two alphas + 1) to 1/2 (one alpha + 1).
    """
    filtered = compute_weights(conn, "decay", pv_option_only=True)
    unfiltered = compute_weights(conn, "decay", pv_option_only=False)
    assert unfiltered[8] == pytest.approx(1.0 / 3.0)
    assert filtered[8] == pytest.approx(1.0 / 2.0)


def test_region_weights_ignore_excluded_regions(conn):
    """CHN rows are all analyst/model/fundamental — unreachable."""
    w = compute_weights(conn, "region", pv_option_only=True)
    assert "CHN" not in w
    assert "USA" in w


def test_partially_reachable_alpha_with_pv_plus_option_is_kept(conn):
    """["pv","option"] is entirely inside the restriction."""
    w = compute_weights(conn, "decay", pv_option_only=True)
    # a1, a2 (decay 4) and a3 (decay 8) survive
    assert w[4] == pytest.approx(1.0 / 3.0)
    assert w[8] == pytest.approx(1.0 / 2.0)


def test_unfiltered_mode_still_sees_everything(conn):
    """The old behaviour stays available for comparison."""
    w = compute_weights(conn, "decay", pv_option_only=False)
    assert w[4] == pytest.approx(1.0 / 5.0)


def test_config_weights_respect_the_filter(conn):
    w = compute_config_weights(conn, pv_option_only=True)
    assert ("CHN", "TOP2000U", 0) not in w
    assert ("USA", "TOP3000", 1) in w


def test_test_period_weights_respect_the_filter(conn):
    w = compute_test_period_weights(conn, pv_option_only=True)
    assert "P0Y6M" not in w, "P0Y6M only appears on excluded alphas"
    assert "P1Y" in w


def test_alphas_with_no_category_are_excluded(conn):
    """Absent metadata cannot confirm pv/option, so it must not count."""
    conn.execute("INSERT INTO alpha_results VALUES (?,?,?,?,?,?,?)", ("a7", "USA", "TOP3000", 1, 99, None, None))
    conn.commit()
    w = compute_weights(conn, "decay", pv_option_only=True)
    assert 99 not in w


def test_malformed_category_json_is_excluded(conn):
    conn.execute("INSERT INTO alpha_results VALUES (?,?,?,?,?,?,?)", ("a8", "USA", "TOP3000", 1, 77, "not json", None))
    conn.commit()
    w = compute_weights(conn, "decay", pv_option_only=True)
    assert 77 not in w
