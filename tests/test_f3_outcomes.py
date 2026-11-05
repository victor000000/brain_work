"""Tests for F3 submission_outcomes counter increments."""

from core.db import connect, init_tables


def _mem_conn():
    conn = connect(":memory:")
    init_tables(conn)
    return conn


def _seed_alpha(conn, alpha_id, template, neutralization="MARKET"):
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, status, template, created_at) "
        "VALUES (?, 's', 'e', 'USA', 'TOP3000', 1, ?, 'UNSUBMITTED', ?, 'd')",
        (alpha_id, neutralization, template),
    )
    conn.commit()


def test_record_outcome_increments_submitted_counter():
    """SUBMITTED status increments the submitted column."""
    from runner.submit import _record_outcome

    conn = _mem_conn()
    _seed_alpha(conn, "a1", "power_ratio")

    _record_outcome(conn, "a1", "SUBMITTED")

    row = conn.execute(
        "SELECT submitted, rejected, throttled FROM submission_outcomes "
        "WHERE template='power_ratio' AND region='USA' AND universe='TOP3000' "
        "AND delay=1 AND neutralization='MARKET'"
    ).fetchone()
    assert row == (1, 0, 0)


def test_record_outcome_increments_rejected_counter():
    from runner.submit import _record_outcome

    conn = _mem_conn()
    _seed_alpha(conn, "a1", "power_ratio")

    _record_outcome(conn, "a1", "REJECTED")
    _record_outcome(conn, "a1", "REJECTED")

    row = conn.execute("SELECT submitted, rejected, throttled FROM submission_outcomes").fetchone()
    assert row == (0, 2, 0)


def test_record_outcome_increments_throttled_counter():
    from runner.submit import _record_outcome

    conn = _mem_conn()
    _seed_alpha(conn, "a1", "power_ratio")

    _record_outcome(conn, "a1", "THROTTLED")

    row = conn.execute("SELECT submitted, rejected, throttled FROM submission_outcomes").fetchone()
    assert row == (0, 0, 1)


def test_record_outcome_skips_non_terminal_status():
    """NOT_SUBMITTED, VERIFY_FAILED, etc. don't bump any counter."""
    from runner.submit import _record_outcome

    conn = _mem_conn()
    _seed_alpha(conn, "a1", "power_ratio")

    _record_outcome(conn, "a1", "NOT_SUBMITTED")
    _record_outcome(conn, "a1", "VERIFY_FAILED")

    n = conn.execute("SELECT COUNT(*) FROM submission_outcomes").fetchone()[0]
    assert n == 0


def test_record_outcome_skips_null_template_alphas():
    """Pre-backfill rows have template IS NULL — no row inserted into submission_outcomes."""
    from runner.submit import _record_outcome

    conn = _mem_conn()
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay,"
        " neutralization, status, created_at) "
        "VALUES ('a1', 's', 'e', 'USA', 'TOP3000', 1, 'MARKET', 'UNSUBMITTED', 'd')"
    )
    conn.commit()

    _record_outcome(conn, "a1", "SUBMITTED")  # no exception

    n = conn.execute("SELECT COUNT(*) FROM submission_outcomes").fetchone()[0]
    assert n == 0
