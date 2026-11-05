"""The per-template correlation weight: measured, bounded, and never a block."""

import time

import pytest

from generator import corr_prior
from generator.corr_prior import FLOOR, corr_weight, correlation_failure_rate, load_corr_prior


@pytest.fixture
def conn():
    import duckdb

    c = duckdb.connect(":memory:")
    c.execute(
        "CREATE TABLE alpha_results (alpha_id TEXT PRIMARY KEY, template TEXT, region TEXT, universe TEXT, delay INTEGER)"
    )
    c.execute(
        "CREATE TABLE alpha_check_summary (alpha_id TEXT, pass_count INTEGER, fail_count INTEGER,"
        " warn_count INTEGER, pend_count INTEGER, checked_at TEXT)"
    )
    c.execute(
        "CREATE TABLE check_failures (alpha_id TEXT, check_name TEXT, limit_val TEXT, actual_val TEXT,"
        " first_seen TEXT, last_seen TEXT, seen_count INTEGER)"
    )
    c.execute("CREATE TABLE submission_checks (alpha_id TEXT, check_name TEXT, result TEXT)")
    yield c
    c.close()


def _alpha(conn, aid, template, checked=True, fails=(), cell=("HKG", "TOP800", 1)):
    conn.execute("INSERT INTO alpha_results VALUES (?,?,?,?,?)", (aid, template, *cell))
    if checked:
        conn.execute(
            "INSERT INTO alpha_check_summary VALUES (?,1,0,0,0,?)",
            (aid, time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())),
        )
    if checked:
        conn.execute(
            "INSERT INTO submission_checks VALUES (?,'PROD_CORRELATION',?)",
            (aid, "FAIL" if "PROD_CORRELATION" in fails else "PASS"),
        )
        conn.execute(
            "INSERT INTO submission_checks VALUES (?,'SELF_CORRELATION',?)",
            (aid, "FAIL" if "SELF_CORRELATION" in fails else "PASS"),
        )
    for name in fails:
        conn.execute("INSERT INTO check_failures VALUES (?,?,'0.7','0.9','now','now',1)", (aid, name))


def test_a_shape_that_never_fails_correlation_keeps_full_weight(conn):
    for i in range(20):
        _alpha(conn, f"clean{i}", "ts_backfill_negmean", fails=())
    load_corr_prior(conn)
    assert corr_weight("ts_backfill_negmean") > 0.95


def test_a_shape_that_usually_fails_is_down_weighted_not_removed(conn):
    for i in range(20):
        _alpha(
            conn,
            f"bad{i}",
            "quantile_ts_rank",
            fails=("PROD_CORRELATION",) if i < 10 else (),
        )
    load_corr_prior(conn)
    # Half the checked alphas failed, smoothed by the Beta(1, 9) prior:
    # 1 - (10 + 1) / (20 + 1 + 9) = 0.633.
    assert corr_weight("quantile_ts_rank") == pytest.approx(0.6333, abs=1e-4)


def test_both_arms_count(conn):
    """Self-correlation blocks a submission exactly as production does."""
    _alpha(conn, "a1", "shape_x", fails=("SELF_CORRELATION",))
    _alpha(conn, "a2", "shape_x", fails=())
    load_corr_prior(conn)
    assert corr_weight("shape_x") < 1.0


def test_an_unchecked_shape_is_left_alone(conn):
    """No evidence is not evidence of a problem."""
    _alpha(conn, "a1", "never_checked", checked=False)
    load_corr_prior(conn)
    assert corr_weight("never_checked") == 1.0


def test_a_shape_nobody_reached_the_gate_with_is_left_alone(conn):
    """`check_failures` alone would call this shape clean; the summary is the
    denominator, and with no checks there is no rate to compute."""
    _alpha(conn, "a1", "unreached", checked=False)
    load_corr_prior(conn)
    assert corr_weight("unreached") == 1.0


def test_the_penalty_stops_at_the_floor(conn):
    """The floor only binds past ~80 consecutive failures — a Beta(1,9) prior
    holds 50 of 50 at 0.15. So it is a safety rail against zeroing, not the
    thing that decides the weight; the measurement decides."""
    for i in range(100):
        _alpha(conn, f"awful{i}", "awful", fails=("PROD_CORRELATION",))
    load_corr_prior(conn)
    assert corr_weight("awful") == FLOOR


def test_failure_rate_needs_a_denominator():
    assert correlation_failure_rate(0, 0) == 0.0
    assert 0.0 < correlation_failure_rate(10, 5) < 1.0


def test_the_loader_is_idempotent(conn):
    _alpha(conn, "a1", "shape_y", fails=("PROD_CORRELATION",))
    load_corr_prior(conn)
    first = corr_weight("shape_y")
    load_corr_prior(conn)
    assert corr_weight("shape_y") == first


def test_corr_prior_module_cache_is_isolated(conn):
    """A reload must not leave a previous test's weight behind."""
    _alpha(conn, "a1", "shape_z", fails=("PROD_CORRELATION",))
    load_corr_prior(conn)
    assert corr_weight("shape_z") < 1.0
    assert corr_prior._corr_weight.get("absent", 1.0) == 1.0


def test_a_stale_check_does_not_count(conn):
    """The weight has to describe what the shape produces now.

    `percentile_momentum` carried a 0.586 multiplier from an all-time 44.9%
    failure rate while failing correlation on 7.4% of today's checks — and at a
    37.8% floor rate it was the best-converting shape in the account.
    """
    _alpha(conn, "old", "reformed", fails=("PROD_CORRELATION",))
    conn.execute("UPDATE alpha_check_summary SET checked_at='2020-01-01 00:00:00 UTC' WHERE alpha_id='old'")
    _alpha(conn, "new", "reformed", fails=())
    conn.commit()
    load_corr_prior(conn)
    # Only the recent check counts, and it passed.
    assert corr_weight("reformed") > 0.9


def test_the_window_is_a_week():
    from generator.corr_prior import RECENT_WINDOW_SEC

    assert RECENT_WINDOW_SEC == 7 * 24 * 3600


def test_a_shape_that_always_fails_keeps_only_the_floor(conn):
    """`sector_neutralized` failed 58 of 58 today. The measurement says the
    multiplier belongs near 0.13; the floor is the only thing holding it up."""
    assert corr_weight("never_fails") == 1.0


def test_cell_weights_do_not_export_crowding_to_other_markets(conn):
    for i in range(33):
        _alpha(conn, f"hk{i}", "volume_surge", fails=("PROD_CORRELATION",) if i < 30 else ())
    _alpha(conn, "eu", "volume_surge", cell=("EUR", "TOP2500", 1))
    load_corr_prior(conn)
    assert corr_weight("volume_surge", cell=("HKG", "TOP800", 1)) == pytest.approx(12 / 43)
    assert corr_weight("volume_surge", cell=("EUR", "TOP2500", 1)) == pytest.approx(10 / 11)
    assert corr_weight("volume_surge", cell=("USA", "TOP3000", 1)) == 1.0
    assert corr_weight("volume_surge", cell=("HKG", "TOP500", 1)) == 1.0
    assert corr_weight("volume_surge", cell=("HKG", "TOP800", 0)) == 1.0
    assert corr_weight("volume_surge") == pytest.approx(13 / 44)


def test_cell_cache_replaced_after_new_check_window(conn):
    _alpha(conn, "a", "shape", fails=("SELF_CORRELATION",))
    load_corr_prior(conn)
    assert corr_weight("shape", cell=("HKG", "TOP800", 1)) < 1.0
    conn.execute("UPDATE alpha_check_summary SET checked_at='2020-01-01 00:00:00 UTC'")
    load_corr_prior(conn)
    assert corr_weight("shape", cell=("HKG", "TOP800", 1)) == 1.0


def test_generator_uses_cell_correlation_evidence(conn, monkeypatch):
    from generator import cell_priors, shape_prior
    from generator.weighted_selection.choice import _cell_biased_weights

    def volume_surge():
        return None

    for i in range(100):
        _alpha(conn, f"hk{i}", "volume_surge", fails=("PROD_CORRELATION",))
    load_corr_prior(conn)
    monkeypatch.setattr(cell_priors, "hit_weight", lambda *args: 1.0)
    monkeypatch.setattr(cell_priors, "expected_multiplier", lambda *args: 1.0)
    monkeypatch.setattr(cell_priors, "oos_robustness", lambda *args: 1.0)
    monkeypatch.setattr(shape_prior, "shape_weight", lambda *args: 1.0)
    templates = [(volume_surge, [])]
    hk = _cell_biased_weights(templates, [1.0], ("HKG", "TOP800", 1, "FAST"))
    eu = _cell_biased_weights(templates, [1.0], ("EUR", "TOP2500", 1, "FAST"))
    assert hk == [FLOOR]
    assert eu == [1.0]


def test_latest_passing_correlation_supersedes_historical_failure(conn):
    _alpha(conn, "recovered", "shape", fails=("PROD_CORRELATION",))
    conn.execute("UPDATE submission_checks SET result='PASS' WHERE alpha_id='recovered'")
    load_corr_prior(conn)
    assert corr_weight("shape", cell=("HKG", "TOP800", 1)) == pytest.approx(10 / 11)
    assert conn.execute("SELECT COUNT(*) FROM check_failures").fetchone()[0] == 1


def test_recent_check_with_offset_is_compared_as_an_instant(conn, monkeypatch):
    # Oct 18 04:00 UTC gives a seven-day cutoff of Oct 11 04:00 UTC.
    monkeypatch.setattr(corr_prior.time, "time", lambda: 1792296000)
    _alpha(conn, "recent", "shape", fails=("SELF_CORRELATION",))
    conn.execute("UPDATE alpha_check_summary SET checked_at='2026-10-10T23:30:00-05:00'")
    load_corr_prior(conn)
    assert corr_weight("shape", cell=("HKG", "TOP800", 1)) == pytest.approx(9 / 11)
