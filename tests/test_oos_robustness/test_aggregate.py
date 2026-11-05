"""fetch_oos_robustness_counts returns per-cell (n_with_test, n_robust)
where n_robust is alphas with test_sharpe > 0.5 * is_sharpe (positive IS only)."""

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
        ("A1", "T", "CHN", "U", 0, 2.0, 1.5, '["pv"]'),  # robust (1.5 > 0.5*2.0 = 1.0)
        ("A2", "T", "CHN", "U", 0, 2.0, 1.1, '["pv"]'),  # robust (1.1 > 1.0)
        ("A3", "T", "CHN", "U", 0, 2.0, 0.5, '["pv"]'),  # not robust (0.5 < 1.0)
        ("A4", "T", "CHN", "U", 0, 1.0, -0.2, '["pv"]'),  # not robust
        ("A5", "T", "CHN", "U", 0, -0.5, 0.0, '["pv"]'),  # negative IS — excluded
        ("A6", "T", "CHN", "U", 0, 0.0, None, '["pv"]'),  # test_sharpe NULL — excluded
        # Unreachable pyramids: must not contribute to the posterior at all.
        ("A7", "T", "CHN", "U", 0, 3.0, 3.0, '["fundamental"]'),
        ("A8", "T", "CHN", "U", 0, 3.0, 3.0, None),
    ]
    c.executemany(
        "INSERT INTO alpha_results "
        "(alpha_id, template, region, universe, delay, is_sharpe, test_sharpe, pyramid_categories) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    c.commit()
    yield c
    c.close()


def test_oos_counts_one_cell(conn):
    from generator.priors_loader.aggregate import fetch_oos_robustness_counts

    out = fetch_oos_robustness_counts(conn)
    assert out == {("T", "CHN", "U", 0): (4, 2)}  # n_with_test=4, n_robust=2


def test_oos_counts_skip_unreachable_alphas(conn):
    """fundamental/NULL-pyramid rows are ignored even with perfect OOS sharpe."""
    from generator.priors_loader.aggregate import fetch_oos_robustness_counts

    # A7 (fundamental) and A8 (NULL) would each add (1, 1) if counted.
    assert fetch_oos_robustness_counts(conn) == {("T", "CHN", "U", 0): (4, 2)}
