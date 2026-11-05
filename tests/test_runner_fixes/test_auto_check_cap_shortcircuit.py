"""The run stops once the day's submission cap is seen.

Nothing a run decides while the cap is spent can be submitted before the
boundary, and the cap *masks* the rest of the check set: alphas previewed under
it report `REGULAR_SUBMISSION` alone and turn out to fail three checks once it
lifts (measured 2026-10-07). Continuing would defer the whole queue on no
evidence, at two endpoints' worth of rate limit each.
"""

from checker import auto_check
from tests.test_runner_fixes.auto_check_helpers import _seed


def test_the_run_stops_at_the_cap(monkeypatch, conn):
    _seed(conn, "TOP", 9.0)
    _seed(conn, "SECOND", 8.0)
    _seed(conn, "THIRD", 7.0)
    seen = []

    def cap_only(session, aid):
        seen.append(aid)
        return [
            {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.0},
            {"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4.0, "value": 4.0},
        ]

    monkeypatch.setattr(auto_check, "check_via_get", cap_only)
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert seen == ["TOP"], f"the run kept going past the cap: {seen}"
    # The one it did reach is deferred, not retired, so it survives to the reset.
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary").fetchone()[0] == 0


def test_a_cap_alongside_a_real_failure_does_not_stop_the_run(monkeypatch, conn):
    """Only a cap-*alone* preview is the account's condition; another FAIL is
    the alpha's and is worth recording for the alphas behind it."""
    _seed(conn, "TOP", 9.0)
    _seed(conn, "SECOND", 8.0)
    seen = []

    def cap_and_sharpe(session, aid):
        seen.append(aid)
        return [
            {"name": "LOW_SHARPE", "result": "FAIL", "limit": 1.58, "value": 0.9},
            {"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4.0, "value": 4.0},
        ]

    monkeypatch.setattr(auto_check, "check_via_get", cap_and_sharpe)
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert seen == ["TOP", "SECOND"]
