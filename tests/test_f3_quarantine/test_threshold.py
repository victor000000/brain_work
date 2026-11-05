"""Threshold tests: K rejections / 0 submissions decides quarantine."""

from tests.test_f3_quarantine.conftest import mem_conn, seed_alpha, seed_outcome


def test_quarantine_on_5_rejections_zero_submissions():
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    seed_alpha(conn, "a1", "bad_template")
    seed_outcome(conn, "bad_template", "MARKET", rejected=5, submitted=0)
    conn.commit()

    refresh_priors(conn)

    row = conn.execute("SELECT quarantined, quarantined_at FROM cell_priors WHERE template='bad_template'").fetchone()
    assert row[0] == 1
    assert row[1] is not None


def test_no_quarantine_below_threshold():
    """4 rejections → not quarantined."""
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    seed_alpha(conn, "a1", "borderline_template")
    seed_outcome(conn, "borderline_template", "MARKET", rejected=4, submitted=0)
    conn.commit()

    refresh_priors(conn)
    row = conn.execute("SELECT quarantined FROM cell_priors WHERE template='borderline_template'").fetchone()
    assert row[0] == 0


def test_no_quarantine_when_any_submission_succeeded():
    """5 rejections + 1 submission → not quarantined."""
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    seed_alpha(conn, "a1", "imperfect_template")
    seed_outcome(conn, "imperfect_template", "MARKET", rejected=5, submitted=1)
    conn.commit()

    refresh_priors(conn)
    row = conn.execute("SELECT quarantined FROM cell_priors WHERE template='imperfect_template'").fetchone()
    assert row[0] == 0


def test_quarantine_marginalizes_over_neutralization():
    """3+2 rejections across two neutralizations → marginal cell has 5 → quarantined."""
    from generator.priors_loader import refresh_priors

    conn = mem_conn()
    seed_alpha(conn, "a1", "marg_template")
    seed_outcome(conn, "marg_template", "MARKET", rejected=3)
    seed_outcome(conn, "marg_template", "SECTOR", rejected=2)
    conn.commit()

    refresh_priors(conn)
    row = conn.execute("SELECT quarantined FROM cell_priors WHERE template='marg_template'").fetchone()
    assert row[0] == 1
