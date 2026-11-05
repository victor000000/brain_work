"""Near-miss polishing: which alphas get queued, and when a batch runs."""

from runner.explore_helpers import polish
from storage.store_checks import POLISH_MIN_PASSES, store_checks
from tests.test_polish_helpers import _alpha, _checks, conn

__all__ = ["conn"]

# ---------------------------------------------------------------- queueing ---


def test_one_failure_alpha_is_queued(conn):
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    row = conn.execute(
        "SELECT alpha_id, expression, region, neutralization, attempts FROM polish_candidates"
    ).fetchone()
    assert row == ("A1", "rank(close)", "HKG", "SLOW", 0)


def test_two_failures_is_not_queued(conn):
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 2))
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 0


def test_a_non_converting_failure_is_not_queued(conn):
    """The 2026-10-14 measurement: these classes converted 0 of 59 expressions.

    `LOW_ROBUST_UNIVERSE_SHARPE.WITH_RATIO` alone supplied 47 of the 100
    candidates the queue ever held, and none produced a clean alpha — the
    settings axes cannot move a sub-universe sharpe ratio. Admitting them spent
    four simulations per expression re-growing the same failure.
    """
    _alpha(conn)
    checks = _checks(POLISH_MIN_PASSES, 0)
    checks.append({"name": "LOW_ROBUST_UNIVERSE_SHARPE.WITH_RATIO", "result": "FAIL", "limit": 1.13, "value": 0.57})
    store_checks(conn, "A1", checks)
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 0


def test_concentrated_weight_is_excluded_after_the_axis_failed_its_test(conn):
    """Excluded again 2026-10-16, on a live measurement: the axis's first
    candidate read CONCENTRATED_WEIGHT 0.234203 at t=0.02 against 0.233743
    at t=0.1 — unmoved to the third decimal. The re-admission of 10-15 was
    right that the axis was untested; its test came back negative.
    """
    _alpha(conn)
    checks = _checks(POLISH_MIN_PASSES, 0)
    checks.append({"name": "CONCENTRATED_WEIGHT", "result": "FAIL", "limit": 0.1, "value": 0.31})
    store_checks(conn, "A1", checks)
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 0


def test_a_converting_class_still_queues(conn):
    """`PROD_CORRELATION` is 11 of 32 on the same measurement — the queue exists for classes like it."""
    _alpha(conn)
    checks = _checks(POLISH_MIN_PASSES, 0)
    checks.append({"name": "PROD_CORRELATION", "result": "FAIL", "limit": 0.7, "value": 0.72})
    store_checks(conn, "A1", checks)
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 1


def test_too_few_passes_is_not_queued(conn):
    """One failure on a weak alpha is not a near-miss — it is just a bad alpha."""
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES - 1, 1))
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 0


def test_cap_only_failure_is_not_a_polish_candidate(conn):
    """The submission cap is the account's condition, not this alpha's.

    A settings variant cannot fix `limit=4 val=4`, and — worse — storing the
    cap as the alpha's one failing check writes an `alpha_check_summary` row,
    which is the auto-checker's "already checked" filter: the alpha is retired
    and can never be submitted once the cap lifts. 51 submission-ready alphas
    were lost that way between 2026-10-06 20:48 and the fix.
    """
    _alpha(conn)
    checks = _checks(POLISH_MIN_PASSES, 0)
    checks.append({"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4.0, "value": 4.0})
    store_checks(conn, "A1", checks)
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary").fetchone()[0] == 0
    # The check rows are still written, so the outcome stays visible.
    row = conn.execute(
        "SELECT result FROM submission_checks WHERE alpha_id='A1' AND check_name='REGULAR_SUBMISSION'"
    ).fetchone()
    assert row == ("FAIL",)


def test_cap_alongside_a_real_failure_is_still_decided(conn):
    """Only a cap-*alone* response is transient; another failure is the alpha's."""
    _alpha(conn)
    checks = _checks(POLISH_MIN_PASSES, 1)
    checks.append({"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4.0, "value": 4.0})
    store_checks(conn, "A1", checks)
    row = conn.execute("SELECT fail_count FROM alpha_check_summary WHERE alpha_id='A1'").fetchone()
    assert row == (2,)


def test_pending_check_does_not_disqualify(conn):
    """Pending checks are routine (MATCHES_THEMES, POWER_POOL_*) — requiring
    pend==0 rejected every recent candidate and starved the queue."""
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1, n_pend=2))
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 1


def test_alpha_without_a_stored_row_is_skipped(conn):
    store_checks(conn, "ghost", _checks(POLISH_MIN_PASSES, 1))
    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 0


def test_requeue_does_not_reset_the_attempt_budget(conn):
    _alpha(conn)
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    conn.execute("UPDATE polish_candidates SET attempts = 2")
    store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
    assert conn.execute("SELECT attempts FROM polish_candidates").fetchone()[0] == 2


# -------------------------------------------------------------- scheduling ---


def test_should_polish_is_deterministic_on_the_batch_index():
    n = polish.POLISH_EVERY
    assert [i for i in range(1, n * 2 + 1) if polish.should_polish(i)] == [n, n * 2]
    # Exactly one batch in POLISH_EVERY, whatever the starting point.
    assert sum(polish.should_polish(i) for i in range(n * 100)) == 100


def test_the_same_expression_is_queued_once(conn):
    """Polish queues expressions, not alpha ids.

    A re-run produces a new alpha carrying the same expression, so without this
    the queue feeds itself: on 2026-10-07 it held 191 candidates covering 22
    expressions, one of them 75 times. Every duplicate spends its own four
    re-runs producing a signal already simulated, and they then fail
    SELF_CORRELATION against each other.
    """
    _alpha(conn, "A1", expr="rank(close)")
    _alpha(conn, "A2", expr="rank(close)")
    _alpha(conn, "A3", expr="rank(volume)")
    for aid in ("A1", "A2", "A3"):
        store_checks(conn, aid, _checks(POLISH_MIN_PASSES, 1))
    rows = conn.execute("SELECT alpha_id FROM polish_candidates ORDER BY alpha_id").fetchall()
    assert rows == [("A1",), ("A3",)]


def test_enqueue_reports_only_what_it_actually_queued(conn, caplog):
    """The log used to claim an enqueue the expression guard had rejected.

    Five candidates on 2026-10-07 were reported "queued for a settings-variant
    re-run" while a pre-existing row for the same expression excluded every
    one, so a starved queue read as a fed one.
    """
    import logging

    _alpha(conn, aid="A1", expr="rank(close)")
    _alpha(conn, aid="A2", expr="rank(close)")
    with caplog.at_level(logging.INFO, logger="brain.check"):
        store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
        caplog.clear()
        store_checks(conn, "A2", _checks(POLISH_MIN_PASSES, 1))

    assert conn.execute("SELECT COUNT(*) FROM polish_candidates").fetchone()[0] == 1
    assert not [r for r in caplog.records if "queued for a settings-variant" in r.getMessage()], (
        "a rejected enqueue was reported as queued"
    )
    assert [r for r in caplog.records if "not queued" in r.getMessage()]


def test_enqueue_says_which_reason_rejected_it(conn, caplog):
    """An expression already queued and a missing alpha row mean opposite things.

    Both used to log the same "no stored alpha, or its expression already
    entered the queue", so a genuinely missing `alpha_results` row — which
    would be a bug — read exactly like the anti-feed guard doing its job.
    """
    import logging

    _alpha(conn, aid="A1", expr="rank(close)")
    with caplog.at_level(logging.INFO, logger="brain.check"):
        # Same expression as A1: rejected by the guard, not by a missing row.
        _alpha(conn, aid="A2", expr="rank(close)")
        store_checks(conn, "A1", _checks(POLISH_MIN_PASSES, 1))
        caplog.clear()
        store_checks(conn, "A2", _checks(POLISH_MIN_PASSES, 1))
    dup = [r.getMessage() for r in caplog.records if "not queued" in r.getMessage()]
    assert dup and "expression already entered the polish queue" in dup[0], dup

    # An alpha with no stored row: same gate, different cause, and the warning
    # level is what makes it findable.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="brain.check"):
        store_checks(conn, "NOPE", _checks(POLISH_MIN_PASSES, 1))
    missing = [r for r in caplog.records if "not queued" in r.getMessage()]
    assert missing and "no alpha_results row" in missing[0].getMessage(), missing
    assert missing[0].levelno == logging.WARNING, "a missing alpha row is not routine"
