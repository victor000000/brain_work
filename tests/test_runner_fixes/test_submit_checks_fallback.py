"""The fallback GET path must not write alpha_check_summary.

Split out of `test_submit_checks.py`; see that module for the submit-path
tests. A summary row here would permanently exclude a retryable alpha.
"""

from runner import submit_checks as sc


def test_fallback_get_pass_writes_no_summary(monkeypatch, conn):
    monkeypatch.setattr(
        sc,
        "check_via_get",
        lambda session, alpha_id: [{"name": "LOW_SHARPE", "result": "PASS"}],
    )

    result = sc.fallback_get_check(None, conn, "A3", 500)

    assert result == "PASS_BUT_SUBMIT_FAILED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM submission_checks").fetchone()[0] == 0


def test_fallback_get_fail_is_reported_without_summary(monkeypatch, conn):
    monkeypatch.setattr(
        sc,
        "check_via_get",
        lambda session, alpha_id: [{"name": "LOW_SHARPE", "result": "FAIL"}],
    )

    result = sc.fallback_get_check(None, conn, "A4", 429)

    assert result == "FAIL:1"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary").fetchone()[0] == 0


def test_fallback_get_error_is_not_a_rejection(monkeypatch, conn):
    monkeypatch.setattr(
        sc,
        "check_via_get",
        lambda session, alpha_id: [
            {"name": "CLUSTER_TEST", "result": "ERROR"},
            {"name": "PROD_CORRELATION", "result": "PENDING"},
        ],
    )

    result = sc.fallback_get_check(None, conn, "A7", 500)

    assert result == "CHECK_FAILED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary").fetchone()[0] == 0


def test_a_fallback_get_that_never_answered_defers_the_alpha(monkeypatch, conn):
    """A GET that timed out learned nothing, so the alpha must be deferred.

    `CHECK_FAILED` is not in `checker.auto_check_alpha.UNDECIDED_OUTCOMES`, so
    `_check_alpha` deletes the deferral row after it; the alpha then keeps its
    sharpe rank, heads the next check run and spends another preview and submit
    on a platform that is timing out. Measured 2026-10-08 18:51: `omWlgVxk`
    (sharpe 1.70) reached this line on a read timeout with its deferral
    accounting at zero.
    """
    monkeypatch.setattr(sc, "check_via_get", lambda session, alpha_id: None)

    # `None` is the status_code `check_via_submit` returns when the POST never
    # produced an HTTP answer; it is what carries the flow into this path.
    result = sc.fallback_get_check(None, conn, "A9", None)

    assert result == "CHECK_FAILED"
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='A9'").fetchone()[0] == 1
    # Still no summary: the alpha has to stay eligible for a later pass.
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary").fetchone()[0] == 0


def test_a_decided_fallback_get_still_leaves_alone_the_deferral(monkeypatch, conn):
    """Only the undecided returns defer; a real FAIL must not look undecided."""
    monkeypatch.setattr(
        sc,
        "check_via_get",
        lambda session, alpha_id: [{"name": "LOW_SHARPE", "result": "FAIL", "limit": 1.58, "value": 0.68}],
    )

    assert sc.fallback_get_check(None, conn, "A10", 500) == "FAIL:1"
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals").fetchone()[0] == 0
