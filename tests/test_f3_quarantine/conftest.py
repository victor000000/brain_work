"""Shared fixtures for F3 quarantine tests."""

from core.db import connect, init_tables


def mem_conn():
    """Fresh in-memory DB with the simulation schema applied."""
    conn = connect(":memory:")
    init_tables(conn)
    return conn


def seed_alpha(conn, alpha_id, template, is_sharpe=0.5):
    # pyramid_categories must be reachable (pv/option): priors fitting skips
    # alphas the generator cannot reproduce.
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, is_sharpe, status, template, pyramid_categories, created_at) "
        "VALUES (?, 's', 'e', 'USA', 'TOP3000', 1, 'MARKET', ?, 'UNSUBMITTED', ?, '[\"pv\"]', 'd')",
        (alpha_id, is_sharpe, template),
    )


def seed_outcome(conn, template, neutralization, submitted=0, rejected=0, throttled=0):
    conn.execute(
        "INSERT INTO submission_outcomes VALUES (?, 'USA', 'TOP3000', 1, ?, ?, ?, ?)",
        (template, neutralization, submitted, rejected, throttled),
    )
