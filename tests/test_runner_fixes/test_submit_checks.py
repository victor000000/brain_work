"""FIX 6: ALREADY_SUBMITTED is a success, and the fallback GET path must not
write alpha_check_summary (which would permanently exclude retryable alphas).

The fallback-GET tests live in `test_submit_checks_fallback.py`.
"""

import time

from runner import submit_checks as sc
from runner.submit_retry import (
    MAX_SUBMIT_ROUNDS,
    _cooling_submit_rounds,
    _get_retry_count,
    _increment_retry_count,
)


def test_already_submitted_is_success_not_rejection(monkeypatch, conn):
    checks = [{"name": "ALREADY_SUBMITTED", "result": "FAIL", "limit": None, "value": None}]
    monkeypatch.setattr(sc, "check_via_submit", lambda session, alpha_id: (403, checks))

    code, result = sc.try_submit(None, conn, "A1")

    assert (code, result) == (403, "ALREADY_SUBMITTED")
    # A real 403 body is definitive, so its checks are stored.
    assert conn.execute("SELECT COUNT(*) FROM submission_checks WHERE alpha_id='A1'").fetchone()[0] == 1


def test_real_403_failures_report_fail_count(monkeypatch, conn):
    checks = [
        {"name": "LOW_SHARPE", "result": "FAIL", "limit": 1.65, "value": 1.0},
        {"name": "CONCENTRATED_WEIGHT", "result": "PASS", "limit": 0.1, "value": 0.05},
    ]
    monkeypatch.setattr(sc, "check_via_submit", lambda session, alpha_id: (403, checks))

    code, result = sc.try_submit(None, conn, "A2")

    assert (code, result) == (403, "FAIL:1")
    assert conn.execute("SELECT COUNT(*) FROM submission_checks WHERE alpha_id='A2'").fetchone()[0] == 2


def test_errored_check_is_not_a_rejection(monkeypatch, conn):
    """CLUSTER_TEST=ERROR is the platform failing to run a check, not a FAIL.

    It blocked every live submission attempt on 2026-10-03 (75/75 ERROR, never
    PASS); counting it as a failure permanently rejected alphas that passed
    every real check.
    """
    checks = [
        {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.02},
        {"name": "CLUSTER_TEST", "result": "ERROR", "limit": 1, "value": None},
        {"name": "SELF_CORRELATION", "result": "PENDING"},
    ]
    monkeypatch.setattr(sc, "check_via_submit", lambda session, alpha_id: (403, checks))

    code, result = sc.try_submit(None, conn, "A5")

    assert (code, result) == (403, "CHECK_UNAVAILABLE")
    # Stored, but the outcome is transient: the alpha stays retry-eligible.
    assert conn.execute("SELECT COUNT(*) FROM submission_checks WHERE alpha_id='A5'").fetchone()[0] == 3


def test_check_unavailable_does_not_change_status(conn):
    from runner.submit.outcome import update_alpha_status

    conn.execute("INSERT INTO alpha_results (alpha_id, status) VALUES ('A6', 'THROTTLED')")
    update_alpha_status(conn, "A6", "CHECK_UNAVAILABLE")

    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='A6'").fetchone()[0] == "THROTTLED"


def test_the_post_is_gated_after_max_undecided_rounds(monkeypatch, conn):
    """The count is written by both undecided paths and read at one gate.

    It used to be read only on the 403 path, so a `201` that never set
    `dateSubmitted` incremented it and nothing consulted it: `vR2jeq9G`
    collected six void 201s on 2026-10-07 while the rest of the queue paid for
    the re-POSTs. Deferring the alpha without gating the POST only slowed that
    loop, it did not bound it.
    """
    from runner.submit import flow

    monkeypatch.setattr(flow, "ensure_description", lambda *a: None)
    posted = []
    monkeypatch.setattr(flow, "try_submit", lambda *a: posted.append(1) or (403, None))
    for _ in range(MAX_SUBMIT_ROUNDS):
        _increment_retry_count(conn, "A7")

    assert flow._do_check_and_submit(None, conn, "A7") == "CHECK_UNAVAILABLE_GIVEUP"
    assert not posted, "the gate let a POST through"
    # Still eligible, just sent to the back: never retired for a platform state.
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='A7'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='A7'").fetchone()[0] == 0


def test_the_gate_lapses_when_the_cooldown_expires(monkeypatch, conn):
    """A spent count must bar a POST for a while, never for good.

    The gate compared the count to `MAX_SUBMIT_ROUNDS` with nothing ever
    lowering it, so the first five undecided rounds retired the alpha. What
    leaves a submit undecided is platform state — measured 2026-10-08, all 32
    alphas holding a spent count passed every check but `POWER_POOL_SUBMISSION`,
    the account's own allowance, which resets. The deferral backoff already
    treats the same condition as a cooldown; this is its other half.
    """
    from runner.submit import flow

    monkeypatch.setattr(flow, "ensure_description", lambda *a: None)
    posted = []
    monkeypatch.setattr(flow, "try_submit", lambda *a: posted.append(1) or (403, None))
    for _ in range(MAX_SUBMIT_ROUNDS):
        _increment_retry_count(conn, "A9")

    assert flow._do_check_and_submit(None, conn, "A9") == "CHECK_UNAVAILABLE_GIVEUP"

    # Age the marker past the cooldown, exactly as `_increment_retry_count`
    # would have written it six hours ago.
    stale = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() - 7 * 3600))
    conn.execute("UPDATE check_failures SET last_seen=? WHERE alpha_id='A9' AND check_name='RETRY_ATTEMPT'", (stale,))
    conn.commit()

    assert flow._do_check_and_submit(None, conn, "A9") != "CHECK_UNAVAILABLE_GIVEUP"
    assert posted, "the cooldown lapsed and the gate still blocked the POST"


def test_the_cooldown_ignores_a_count_below_the_cap(conn):
    """A spend under the cap is never gated, however old the marker is."""
    stale = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() - 30 * 24 * 3600))
    conn.execute(
        """INSERT INTO check_failures
               (alpha_id, check_name, limit_val, actual_val, first_seen, last_seen, seen_count)
           VALUES ('B1', 'RETRY_ATTEMPT', NULL, NULL, ?, ?, ?)""",
        (stale, stale, MAX_SUBMIT_ROUNDS - 1),
    )
    conn.commit()

    assert _cooling_submit_rounds(conn, "B1") == 0


def test_the_retry_counter_advances(monkeypatch, conn):
    """The give-up branch is unreachable if the marker is never read back.

    `_increment_retry_count` writes a `RETRY_ATTEMPT` row; the reader looked at
    a set of check names that excludes it, so the count stayed 0 forever.
    """
    checks = [{"name": "PROD_CORRELATION", "result": "PENDING"}]
    monkeypatch.setattr(sc, "check_via_submit", lambda session, alpha_id: (403, checks))
    for expected in (1, 2, 3):
        sc.try_submit(None, conn, "A8")
        assert _get_retry_count(conn, "A8") == expected


def test_a_verify_timeout_counts_the_round_and_defers(monkeypatch, conn):
    """A 201 whose confirming GET times out is as undecided as a PENDING one.

    Both `VERIFY_FAILED` returns used to skip the count and the deferral, and
    `_check_alpha` then deleted the deferral row — because VERIFY_FAILED was
    not in `UNDECIDED_OUTCOMES`. So a slow platform produced alphas that headed
    every check run and were re-POSTed forever, which is the unbounded loop the
    count exists to bound. Measured 2026-10-08: `1YZdJpeJ`, `gJZ3AOAl` and
    `rKeW1wVo` all returned VERIFY_FAILED on a read timeout within ten minutes.
    """
    from runner import verify_submit as vs

    def boom(session, alpha_id):
        raise TimeoutError("read timeout")

    monkeypatch.setattr(vs, "_get_alpha", boom)
    assert vs.verify_submission(None, conn, "V1") == "VERIFY_FAILED"

    assert _get_retry_count(conn, "V1") == 1, "the undecided round was not counted"
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='V1'").fetchone()[0] == 1


def test_a_non_200_verify_counts_the_round_too(monkeypatch, conn):
    """The other VERIFY_FAILED return — a non-200 GET — must count as well."""
    from runner import verify_submit as vs

    monkeypatch.setattr(vs, "_get_alpha", lambda session, alpha_id: (503, None, None))
    assert vs.verify_submission(None, conn, "V2") == "VERIFY_FAILED"

    assert _get_retry_count(conn, "V2") == 1
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='V2'").fetchone()[0] == 1


def test_verify_failed_keeps_the_deferral(conn):
    """The deferral is the count's only visible effect, so clearing it hides it."""
    from checker.auto_check_alpha import UNDECIDED_OUTCOMES

    assert "VERIFY_FAILED" in UNDECIDED_OUTCOMES


def test_an_undecided_outcome_keeps_its_deferral(conn):
    """`_check_alpha` deletes the deferral for every outcome it calls decided.

    A deferral is written by an undecided round — CHECK_FAILED by
    `submit_checks._undecided`, PENDING/VERIFY_FAILED by
    `verify_submit._count_undecided`, QUOTA_BLOCKED by `submit_quota` — so it
    must survive the DELETE, or `attempts` never reaches the selector's
    backoff and the alpha re-enters every run as a first-time offender.
    """
    from checker.auto_check_alpha import _check_alpha

    preview = [
        {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.0},
        {"name": "PROD_CORRELATION", "result": "PASS", "limit": 0.7, "value": 0.3},
        {"name": "SELF_CORRELATION", "result": "PASS", "limit": 0.7, "value": 0.2},
    ]
    for outcome in ("CHECK_FAILED", "PENDING", "QUOTA_BLOCKED", "VERIFY_FAILED"):
        aid = f"D{outcome}"
        sc._undecided(conn, aid)  # the production writer of the deferral
        _check_alpha(
            None,
            conn,
            aid,
            1.7,
            check_via_get=lambda session, alpha_id: preview,
            # `outcome=outcome` binds the value at definition time; the loop
            # variable itself would be a late binding (and lint-flagged).
            check_and_submit=lambda session, c, alpha_id, outcome=outcome: outcome,
        )
        assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id=?", (aid,)).fetchone() == (1,)

    # ...and a decided one still clears it, so the alpha can move on.
    sc._undecided(conn, "DECIDED")
    _check_alpha(
        None,
        conn,
        "DECIDED",
        1.7,
        check_via_get=lambda session, alpha_id: preview,
        check_and_submit=lambda session, c, alpha_id: "FAIL:2",
    )
    assert conn.execute("SELECT COUNT(*) FROM check_deferrals WHERE alpha_id='DECIDED'").fetchone()[0] == 0
