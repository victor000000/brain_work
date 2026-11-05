"""cell_priors.hit_weight: prior, stored value, quarantine override, cache reload."""

import time

from tests.test_f3_priors.conftest import mem_conn


def test_hit_weight_unknown_cell_returns_prior_mean():
    """A cell with no observations returns the Beta(1, 49) prior mean of 1/50 = 0.02."""
    from generator import cell_priors

    conn = mem_conn()
    cell_priors.load_priors(conn)
    w = cell_priors.hit_weight("missing_template", "USA", "TOP3000", 1)
    assert abs(w - 0.02) < 1e-9


def test_hit_weight_known_cell_returns_stored_value():
    """A cell stored in cell_priors returns its hit_weight column verbatim."""
    from generator import cell_priors

    conn = mem_conn()
    conn.execute(
        "INSERT INTO cell_priors "
        "(template, region, universe, delay, count, hits, hit_weight, "
        " quarantined, quarantined_at, refreshed_at) "
        "VALUES ('power_ratio', 'USA', 'TOP3000', 1, 100, 10, 0.073, 0, NULL, ?)",
        (int(time.time()),),
    )
    conn.commit()
    cell_priors.load_priors(conn)
    w = cell_priors.hit_weight("power_ratio", "USA", "TOP3000", 1)
    assert abs(w - 0.073) < 1e-9


def test_hit_weight_quarantined_cell_returns_zero():
    """A quarantined cell returns 0.0 regardless of stored hit_weight."""
    from generator import cell_priors

    conn = mem_conn()
    conn.execute(
        "INSERT INTO cell_priors "
        "(template, region, universe, delay, count, hits, hit_weight, "
        " quarantined, quarantined_at, refreshed_at) "
        "VALUES ('power_ratio', 'USA', 'TOP3000', 1, 5, 0, 0.0196, 1, ?, ?)",
        (int(time.time()), int(time.time())),
    )
    conn.commit()
    cell_priors.load_priors(conn)
    w = cell_priors.hit_weight("power_ratio", "USA", "TOP3000", 1)
    assert w == 0.0


def test_load_priors_replaces_cache_on_each_call():
    """A second load_priors invocation drops cells removed from the table."""
    from generator import cell_priors

    conn = mem_conn()
    conn.execute(
        "INSERT INTO cell_priors "
        "(template, region, universe, delay, count, hits, hit_weight, "
        " quarantined, quarantined_at, refreshed_at) "
        "VALUES ('t1', 'USA', 'TOP3000', 1, 10, 1, 0.04, 0, NULL, ?)",
        (int(time.time()),),
    )
    conn.commit()
    cell_priors.load_priors(conn)
    assert cell_priors.hit_weight("t1", "USA", "TOP3000", 1) == 0.04

    # Replace the table contents.
    conn.execute("DELETE FROM cell_priors")
    conn.commit()
    cell_priors.load_priors(conn)
    # t1 is no longer cached → returns prior mean.
    assert abs(cell_priors.hit_weight("t1", "USA", "TOP3000", 1) - 0.02) < 1e-9
