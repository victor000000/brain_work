"""FIX 5: a deferred alpha sorts to the back of the queue, and reaching the
submission step clears its deferral.

Deferral is now written only by the submission cap — an undecided correlation
arm submits instead (see `test_auto_check_correlation`). The queue-ordering
property still matters for the cap case: a cap-deferred alpha keeps no summary,
so it stays eligible, and the queue is ordered by sharpe.
"""

import time

from checker import auto_check
from checker.auto_check_queue import DEFERRAL_BACKOFF_AFTER, DEFERRAL_BACKOFF_SEC
from tests.test_runner_fixes.auto_check_helpers import _gates_pass, _seed  # noqa: F401


def _stamp(seconds_ago=0):
    """A `last_at` in the column's own format (the comparison is textual)."""
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() - seconds_ago))


def _defer(conn, alpha_id, attempts, last_at):
    conn.execute(
        "INSERT INTO check_deferrals (alpha_id, attempts, last_at) VALUES (?,?,?)",
        (alpha_id, attempts, last_at),
    )
    conn.commit()


def test_a_chronic_alpha_is_held_out_of_the_run(conn):
    """32 alphas produced 568 giveups; 30 of them with 5+ each.

    Each costs a full 90s preview deadline, so a handful of chronic alphas can
    eat a whole CHECK_RUN_BUDGET_SEC run and starve everything behind them.
    """
    _seed(conn, "CHRONIC", 9.0)
    _seed(conn, "FRESH", 1.7)
    _defer(conn, "CHRONIC", 28, _stamp())

    ids = [aid for aid, _sh in auto_check._select_candidates(conn, 10)]
    assert ids == ["FRESH"], ids


def test_a_chronic_alpha_returns_once_the_cooldown_expires(conn):
    """It is a cooldown, not a blacklist: what blocks a preview is platform
    state, and that changes — the alpha deserves another look."""
    _seed(conn, "CHRONIC", 9.0)
    _defer(conn, "CHRONIC", 28, _stamp(DEFERRAL_BACKOFF_SEC + 60))

    ids = [aid for aid, _sh in auto_check._select_candidates(conn, 10)]
    assert ids == ["CHRONIC"], ids


def test_below_the_threshold_it_still_only_sorts_last(conn):
    """The backoff must not change what a first or second failure does."""
    _seed(conn, "ONCE", 9.0)
    _seed(conn, "FRESH", 1.7)
    _defer(conn, "ONCE", DEFERRAL_BACKOFF_AFTER - 1, _stamp())

    ids = [aid for aid, _sh in auto_check._select_candidates(conn, 10)]
    assert ids == ["FRESH", "ONCE"], ids


def test_a_never_deferred_alpha_is_not_dropped(conn):
    """Their `attempts` is NULL, and `NOT (NULL >= 3 AND ...)` is NULL, which
    drops the row — the trap that would empty the queue of everything working."""
    _seed(conn, "FRESH", 1.7)

    ids = [aid for aid, _sh in auto_check._select_candidates(conn, 10)]
    assert ids == ["FRESH"], ids


def test_a_deferred_alpha_goes_to_the_back_of_the_queue(monkeypatch, conn):
    """A cap deferral must not let one alpha head every run.

    An undecided alpha keeps no summary, so it stays eligible — and the queue
    is ordered by sharpe, so it would be first every time. Once a run is
    bounded by wall clock that starves everything below it.
    """
    _seed(conn, "TOP", 9.0)
    _seed(conn, "SECOND", 8.0)
    seen = []

    monkeypatch.setattr(auto_check, "check_via_get", lambda s, a: [{"name": "X", "result": "PASS"}])
    monkeypatch.setattr(auto_check, "check_and_submit", lambda s, c, aid: seen.append(aid) or "CHECK_UNAVAILABLE")

    # A previous run hit the submission cap on TOP.
    conn.execute("INSERT INTO check_deferrals (alpha_id, attempts, last_at) VALUES ('TOP', 1, 'now')")
    conn.commit()

    auto_check.check_new_alphas(None, conn, limit=20)

    assert seen == ["SECOND", "TOP"], f"the deferred alpha was not sent to the back: {seen}"


def test_an_undecided_outcome_keeps_the_deferral(monkeypatch, conn):
    """The count is what the backoff reads, so an undecided outcome must not
    wipe it.

    `flow.py` increments `attempts` on every undecided submit round, but the
    DELETE ran *before* the submit and reset it to zero first — so an alpha
    with 28 failed previews re-entered every run as a first-time offender and
    the count could never reach the backoff threshold.
    """
    _seed(conn, "TOP", 9.0)
    _defer(conn, "TOP", 2, _stamp())
    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: "CHECK_UNAVAILABLE_GIVEUP")

    auto_check.check_new_alphas(None, conn, limit=20)

    row = conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='TOP'").fetchone()
    assert row is not None, "the giveup wiped the deferral it is supposed to accumulate"
    assert row[0] == 2


def test_reaching_the_submit_clears_the_deferral(monkeypatch, conn):
    """Once the alpha is submitted, it must not keep sorting last."""
    _seed(conn, "TOP", 9.0)
    _seed(conn, "SECOND", 8.0)
    for aid in ("TOP", "SECOND"):
        conn.execute("INSERT INTO check_deferrals (alpha_id, attempts, last_at) VALUES (?, 1, 'now')", (aid,))
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals").fetchone()[0] == 2

    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: "FAIL:1")
    auto_check.check_new_alphas(None, conn, limit=20)

    assert conn.execute("SELECT COUNT(*) FROM check_deferrals").fetchone()[0] == 0


def test_undecided_submit_rounds_back_off_in_the_real_queue(monkeypatch, conn):
    from checker.auto_check_alpha import _check_alpha
    from runner import submit_checks
    from runner.submit import flow

    _seed(conn, "BLOCKED", 9.0)
    _seed(conn, "FRESH", 2.0)
    monkeypatch.setattr(flow, "ensure_description", lambda *a: None)
    monkeypatch.setattr(
        submit_checks,
        "check_via_submit",
        lambda session, aid: (403, [{"name": "CLUSTER_TEST", "result": "ERROR"}]),
    )

    for attempt in range(DEFERRAL_BACKOFF_AFTER):
        _check_alpha(
            None,
            conn,
            "BLOCKED",
            9.0,
            check_via_get=lambda s, a: [{"name": "LOW_SHARPE", "result": "PASS"}],
            check_and_submit=flow.check_and_submit,
        )
        assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='BLOCKED'").fetchone() == (
            attempt + 1,
        )
        if attempt == 0:
            assert [aid for aid, _ in auto_check._select_candidates(conn, 10)] == ["FRESH", "BLOCKED"]

    assert [aid for aid, _ in auto_check._select_candidates(conn, 10)] == ["FRESH"]
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='BLOCKED'").fetchone() == (0,)
