"""refresh_cell_yield_posterior aggregates cleared-check counts per
(region, universe, delay) and writes Beta(1,14000) posteriors."""

import pytest

from core.db import connect
from core.db.schema_sql import SCHEMA_SQL


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript(SCHEMA_SQL)
    c.execute("ALTER TABLE alpha_results ADD COLUMN template TEXT")
    c.execute("ALTER TABLE alpha_results ADD COLUMN pyramid_categories TEXT")
    # CHN: 10 alphas, 2 eligible
    rows = [
        ("A1", "T", "CHN", "TOP2000U", 0, "NONE", 2.0, 1.5, 0.3, 1.0, '["pv"]'),
        ("A2", "T", "CHN", "TOP2000U", 0, "NONE", 2.1, 1.2, 0.4, 1.0, '["pv"]'),
        ("A3", "T", "CHN", "TOP2000U", 0, "NONE", 1.0, 0.5, 0.3, 1.0, '["pv"]'),
    ]
    for i in range(7):
        rows.append((f"A{10 + i}", "T", "CHN", "TOP2000U", 0, "NONE", 0.5, 0.0, 0.3, 1.0, '["pv"]'))
    # EUR: 5 alphas, 0 eligible
    for i in range(5):
        rows.append((f"B{i}", "T", "EUR", "TOP400", 0, "NONE", 0.3, 0.0, 0.3, 1.0, '["pv"]'))
    # Unreachable pyramid (fundamental) with elite stats — must not be counted.
    rows.append(("C1", "T", "CHN", "TOP2000U", 0, "NONE", 5.0, 5.0, 0.3, 5.0, '["fundamental"]'))
    c.executemany(
        "INSERT INTO alpha_results "
        "(alpha_id, template, region, universe, delay, neutralization, "
        " is_sharpe, is_fitness, is_turnover, test_sharpe, pyramid_categories) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    # A2 cleared its checks; A1 was checked and failed one. The success event is
    # the check outcome, not the local gate — measured 2026-10-12, CHN's gate
    # passers converted 0 times in 78 checks, so paying the cell for them paid
    # it for the quantity its universe effect inflates.
    c.executemany(
        "INSERT INTO alpha_check_summary (alpha_id, pass_count, fail_count, warn_count, pend_count, checked_at) "
        "VALUES (?, ?, ?, ?, ?, 'now')",
        [("A2", 5, 0, 1, 0), ("A1", 4, 1, 1, 0)],
    )
    c.commit()
    yield c
    c.close()


def test_refresh_writes_posterior(conn):
    from generator.priors_loader._constants import _YIELD_ALPHA, _YIELD_BETA
    from generator.priors_loader.yield_posterior import refresh_cell_yield_posterior

    refresh_cell_yield_posterior(conn)
    rows = dict(
        ((r, u, d), (cnt, cleared, post))
        for r, u, d, cnt, cleared, post, _ in conn.execute(
            "SELECT region, universe, delay, count, eligible, posterior, refreshed_at FROM cell_yield_posterior"
        )
    )
    assert rows[("CHN", "TOP2000U", 0)][0] == 10
    assert rows[("EUR", "TOP400", 0)][0] == 5
    # A2 cleared and A1 did not, so CHN is 1 — and the EUR cell, whose alphas
    # were never checked at all, is 0.
    assert rows[("CHN", "TOP2000U", 0)][1] == 1
    assert rows[("EUR", "TOP400", 0)][1] == 0
    # (1 + 1) / (1 + 14000 + 10), against a prior mean of 1/14001.
    assert rows[("CHN", "TOP2000U", 0)][2] == pytest.approx((_YIELD_ALPHA + 1) / (_YIELD_ALPHA + _YIELD_BETA + 10))
    assert rows[("EUR", "TOP400", 0)][2] < rows[("CHN", "TOP2000U", 0)][2]
