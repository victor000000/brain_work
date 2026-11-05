"""refresh_priors writes oos_robustness into cell_priors."""

import pytest

from core.db import connect
from core.db.schema_sql import SCHEMA_SQL


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript(SCHEMA_SQL)
    c.execute("ALTER TABLE alpha_results ADD COLUMN template TEXT")
    c.execute("ALTER TABLE alpha_results ADD COLUMN pyramid_categories TEXT")
    c.commit()
    rows = [
        ("A1", "T", "CHN", "U", 0, 2.0, 1.5, "NONE", '["pv"]'),
        ("A2", "T", "CHN", "U", 0, 2.0, 1.5, "NONE", '["pv"]'),
        ("A3", "T", "CHN", "U", 0, 0.5, -0.2, "NONE", '["pv"]'),
        # Unreachable pyramid — must not change the posterior.
        ("A4", "T", "CHN", "U", 0, 2.0, 1.5, "NONE", '["model"]'),
    ]
    c.executemany(
        "INSERT INTO alpha_results "
        "(alpha_id, template, region, universe, delay, is_sharpe, test_sharpe, neutralization, pyramid_categories) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    c.commit()
    yield c
    c.close()


def test_refresh_writes_oos_robustness(conn):
    from generator.priors_loader.refresh import refresh_priors

    refresh_priors(conn)
    row = conn.execute("SELECT oos_robustness FROM cell_priors WHERE template='T'").fetchone()
    # n_with_test=3, n_robust=2 (A1, A2). Posterior = (1+2)/(1+1+3) = 0.6.
    assert row[0] == pytest.approx(0.6, abs=0.001)
