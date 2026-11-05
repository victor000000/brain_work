"""Shared fixtures for F3 priors tests."""

from core.db import connect, init_tables


def mem_conn():
    """Fresh in-memory DB with the simulation schema applied."""
    conn = connect(":memory:")
    init_tables(conn)
    return conn


def seed_alpha(conn, alpha_id, template, region, universe, delay, is_sharpe, pyramid_categories='["pv"]'):
    """Insert minimal alpha_results row for refresh_priors tests.

    pyramid_categories defaults to a reachable (pv) pyramid: priors fitting
    only counts alphas the generator can reproduce, so a NULL value here would
    silently exclude the row.
    """
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, "
        " delay, is_sharpe, status, template, pyramid_categories, created_at) "
        "VALUES (?, 'sim', 'expr', ?, ?, ?, ?, 'UNSUBMITTED', ?, ?, '2026-04-26')",
        (alpha_id, region, universe, delay, is_sharpe, template, pyramid_categories),
    )
