"""yield_cache.load_cell_yield_posterior + posterior(cell) accessor."""

import pytest

from core.db import connect
from core.db.schema_sql import SCHEMA_SQL


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript(SCHEMA_SQL)
    c.execute(
        "INSERT INTO cell_yield_posterior "
        "(region, universe, delay, count, eligible, posterior, refreshed_at) "
        "VALUES ('CHN', 'TOP2000U', 0, 10, 2, 0.05, 0)"
    )
    c.commit()
    yield c
    c.close()


def test_load_and_lookup(conn):
    from generator.diversity_picker import yield_cache

    yield_cache.load_cell_yield_posterior(conn)
    assert yield_cache.posterior("CHN", "TOP2000U", 0) == pytest.approx(0.05)


def test_unknown_cell_returns_prior_mean(conn):
    from generator.diversity_picker import yield_cache
    from generator.priors_loader._constants import _YIELD_ALPHA, _YIELD_BETA

    yield_cache.load_cell_yield_posterior(conn)
    # Read from the constants rather than restating the number: the prior mean
    # is calibrated to the success event's base rate, and that event changed on
    # 2026-10-12. What this test guards is that an unknown cell gets the mean,
    # not that the mean is any particular value.
    assert yield_cache.posterior("EUR", "TOP400", 0) == pytest.approx(_YIELD_ALPHA / (_YIELD_ALPHA + _YIELD_BETA))
