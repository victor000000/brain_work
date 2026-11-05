"""Queue guards: a quota defers an alpha, and only the account cap stops a run.

The correlation-outage breaker that used to live alongside these tests was
deleted on 2026-10-07 with the endpoint polls it guarded — see
`checker/auto_check_arms.py` for why nothing polls any more.
"""

from checker import auto_check
from tests.test_runner_fixes.auto_check_helpers import _gates_pass, _seed  # noqa: F401


def test_a_submission_cap_failure_defers_instead_of_retiring(monkeypatch, conn):
    """The cap is an account state, not a property of the alpha.

    `REGULAR_SUBMISSION` fails `limit=4 val=4` on every alpha once the four
    submissions are spent. Retiring those alpha permanently excludes them from
    every later check run, so they could never be submitted once the cap lifted
    — 51 were discarded within an hour on 2026-10-06.
    """
    _seed(conn, "CAPPED", 3.0)
    monkeypatch.setattr(auto_check, "check_via_get", lambda s, a: [{"name": "REGULAR_SUBMISSION", "result": "FAIL"}])
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    # Deferred: still eligible, so a later run can submit it.
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='CAPPED'").fetchone()[0] == 0
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='CAPPED'").fetchone()[0] == 1


def test_a_real_failure_alongside_the_cap_still_retires(monkeypatch, conn):
    """Only the cap *alone* defers — a genuine failure still drains the queue."""
    _seed(conn, "BAD", 3.0)
    monkeypatch.setattr(
        auto_check,
        "check_via_get",
        lambda s, a: [{"name": "REGULAR_SUBMISSION", "result": "FAIL"}, {"name": "LOW_2Y_SHARPE", "result": "FAIL"}],
    )
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='BAD'").fetchone()[0] == 1


def test_a_power_pool_preview_fail_defers_without_stopping_the_run(monkeypatch, conn):
    """A quota-only preview FAIL must defer, and must not halt the run.

    `store_checks` already keeps such an alpha out of the summary so it stays
    eligible, but nothing deferred it, so it kept its sharpe rank and headed
    every run — 45s of preview per cycle to be told the same thing. Deferring
    fixes that; halting would be wrong, because the power pool gates only the
    alphas that match it (`omWqeawm` took a real verdict while four neighbours
    were QUOTA_BLOCKED).
    """
    _seed(conn, "POOL", 3.0)
    _seed(conn, "OTHER", 2.0)
    monkeypatch.setattr(
        auto_check,
        "check_via_get",
        lambda s, a: [{"name": "POWER_POOL_SUBMISSION", "result": "FAIL", "limit": 1, "value": 1}],
    )
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    # Deferred and still eligible; never retired for a quota.
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals WHERE alpha_id='POOL'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='POOL'").fetchone()[0] == 0
    # The run continued past it rather than returning CAP_REACHED.
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals WHERE alpha_id='OTHER'").fetchone()[0] == 1
