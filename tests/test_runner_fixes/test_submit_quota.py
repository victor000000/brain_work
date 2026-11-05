"""A spent account-wide quota must not retire an alpha.

`REGULAR_SUBMISSION` (`limit=4 val=4`) and `POWER_POOL_SUBMISSION`
(`limit=1 val=1`) fail on *every* alpha once the allowance is gone, so a FAIL
from either says nothing about the candidate. Both were retiring alphas:
`POWER_POOL_SUBMISSION` cost `d51Z6ZbE` (sharpe 2.40) and `vR2jeq9G` (1.93)
as `REJECTED` on 2026-10-07 before this handling existed.
"""

from runner import submit_checks as sc
from runner.submit.outcome import _result_to_status

QUOTA = {"name": "POWER_POOL_SUBMISSION", "result": "FAIL", "limit": 1, "value": 1}


def test_a_quota_only_failure_does_not_retire_the_alpha(monkeypatch, conn):
    monkeypatch.setattr(sc, "check_via_submit", lambda session, alpha_id: (403, [QUOTA]))

    code, result = sc.try_submit(None, conn, "Q1")

    assert (code, result) == (403, "QUOTA_BLOCKED")
    # Transient, so the alpha stays eligible rather than becoming REJECTED.
    assert _result_to_status(result) is None
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='Q1'").fetchone()[0] == 0
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='Q1'").fetchone()[0] == 1
    # Stored for visibility: the quota is real, it just is not about the alpha.
    assert conn.execute("SELECT COUNT(*) FROM submission_checks WHERE alpha_id='Q1'").fetchone()[0] == 1


def test_a_real_failure_alongside_a_quota_still_retires(monkeypatch, conn):
    """Only a quota *alone* defers — a genuine failure still drains the queue."""
    checks = [QUOTA, {"name": "LOW_SHARPE", "result": "FAIL", "limit": 1.58, "value": 1.2}]
    monkeypatch.setattr(sc, "check_via_submit", lambda session, alpha_id: (403, checks))

    code, result = sc.try_submit(None, conn, "Q2")

    assert (code, result) == (403, "FAIL:1"), "the quota was counted as a rejection"
    assert _result_to_status(result) == "REJECTED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='Q2'").fetchone()[0] == 1


def test_both_quotas_at_once_is_still_only_a_quota(monkeypatch, conn):
    checks = [QUOTA, {"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4, "value": 4}]
    monkeypatch.setattr(sc, "check_via_submit", lambda session, alpha_id: (403, checks))

    assert sc.try_submit(None, conn, "Q3")[1] == "QUOTA_BLOCKED"


def test_store_checks_leaves_a_quota_blocked_alpha_queued(conn):
    from storage.store_checks import store_checks

    store_checks(conn, "Q4", [QUOTA, {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.0}])

    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='Q4'").fetchone()[0] == 0


def test_the_fallback_get_path_also_spares_a_quota(monkeypatch, conn):
    monkeypatch.setattr(sc, "check_via_get", lambda session, alpha_id: [QUOTA])

    assert sc.fallback_get_check(None, conn, "Q5", 500) == "QUOTA_BLOCKED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='Q5'").fetchone()[0] == 0
