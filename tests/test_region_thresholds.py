"""Per-region eligibility thresholds. CHN/d1 needs sharpe >= 2.07,
EUR/d1 keeps 1.58, unknown cells use the conservative default 1.58."""

from runner.submit.eligibility import (
    MIN_SHARPE_DEFAULT,
    REGION_DELAY_MIN_SHARPE,
    eligibility_clause,
)


def test_default_clause_unchanged():
    """No args == today's behaviour: global 1.58 floor."""
    clause = eligibility_clause()
    assert f"is_sharpe >= {MIN_SHARPE_DEFAULT}" in clause
    assert "1.58" in clause


def test_chn_d1_higher_threshold():
    clause = eligibility_clause(region="CHN", delay=1)
    assert "is_sharpe >= 2.07" in clause


def test_eur_d1_unchanged():
    clause = eligibility_clause(region="EUR", delay=1)
    assert "is_sharpe >= 1.58" in clause


def test_unknown_region_falls_back_to_default():
    clause = eligibility_clause(region="MEA", delay=1)
    assert f"is_sharpe >= {MIN_SHARPE_DEFAULT}" in clause


def test_region_delay_min_sharpe_seeded():
    """Confirm the table includes the four regions we know thresholds for."""
    assert REGION_DELAY_MIN_SHARPE[("CHN", 0)] == 2.07
    assert REGION_DELAY_MIN_SHARPE[("CHN", 1)] == 2.07
    assert REGION_DELAY_MIN_SHARPE[("EUR", 0)] == 1.58
    assert REGION_DELAY_MIN_SHARPE[("EUR", 1)] == 1.58


def test_build_eligibility_union_contains_known_cells():
    from runner.submit.eligibility import REGION_DELAY_MIN_SHARPE, build_eligibility_union

    union = build_eligibility_union()
    for region, delay in REGION_DELAY_MIN_SHARPE:
        assert f"region='{region}' AND delay={delay}" in union


def test_build_eligibility_union_empty_dict_returns_default(monkeypatch):
    """Degenerate case: empty REGION_DELAY_MIN_SHARPE must not produce 'NOT ()'."""
    from runner.submit import eligibility

    monkeypatch.setattr(eligibility, "REGION_DELAY_MIN_SHARPE", {})
    union = eligibility.build_eligibility_union()
    assert "NOT ()" not in union
    assert f"is_sharpe >= {eligibility.MIN_SHARPE_DEFAULT}" in union


def test_build_eligibility_union_e2e_chn_vs_eur():
    """Build the union, run it against an in-memory DB with deliberate pass/fail rows."""
    from core.db import connect
    from runner.submit.eligibility import build_eligibility_union

    conn = connect(":memory:")
    conn.execute(
        "CREATE TABLE alpha_results ("
        "alpha_id TEXT, region TEXT, delay INTEGER,"
        " is_sharpe REAL, is_fitness REAL, is_turnover REAL, test_sharpe REAL)"
    )
    conn.executemany(
        "INSERT INTO alpha_results VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("chn-pass", "CHN", 1, 2.10, 1.5, 0.05, 0.5),  # passes CHN 2.07
            ("chn-fail", "CHN", 1, 1.80, 1.5, 0.05, 0.5),  # below CHN, above default
            ("eur-pass", "EUR", 1, 1.60, 1.5, 0.05, 0.5),  # passes EUR 1.58
            ("mea-pass", "MEA", 1, 1.60, 1.5, 0.05, 0.5),  # unknown -> default 1.58
        ],
    )
    conn.commit()
    passing = sorted(
        row[0] for row in conn.execute(f"SELECT alpha_id FROM alpha_results WHERE {build_eligibility_union()}")
    )
    assert passing == ["chn-pass", "eur-pass", "mea-pass"]
    conn.close()


def test_ind_turnover_ceiling_is_the_platforms_not_the_default():
    """IND's HIGH_TURNOVER limit is 0.4; every other region returns 0.7.

    Measured from `submission_checks` (356 IND rows). The band was one global
    0.7, so an IND alpha in (0.4, 0.7] passed the local gate and was sent to a
    check that could only fail it — 13 such alphas on record.
    """
    from core.db import connect
    from runner.submit.eligibility import build_eligibility_union

    conn = connect(":memory:")
    conn.execute(
        "CREATE TABLE alpha_results ("
        "alpha_id TEXT, region TEXT, delay INTEGER,"
        " is_sharpe REAL, is_fitness REAL, is_turnover REAL, test_sharpe REAL)"
    )
    conn.executemany(
        "INSERT INTO alpha_results VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("ind-ok", "IND", 1, 2.0, 1.5, 0.35, 0.5),  # under IND's 0.4
            ("ind-over", "IND", 1, 2.0, 1.5, 0.55, 0.5),  # over IND, under the 0.7 default
            ("hkg-over", "HKG", 1, 2.0, 1.5, 0.55, 0.5),  # same turnover, HKG allows it
        ],
    )
    conn.commit()
    passing = sorted(
        row[0] for row in conn.execute(f"SELECT alpha_id FROM alpha_results WHERE {build_eligibility_union()}")
    )
    assert passing == ["hkg-over", "ind-ok"]
    conn.close()


def test_an_unknown_region_keeps_the_default_turnover_band():
    from runner.submit.eligibility import TURNOVER_MAX, eligibility_clause

    assert f"is_turnover BETWEEN 0.01 AND {TURNOVER_MAX}" in eligibility_clause("XYZ", 1)
