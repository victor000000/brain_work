"""FIXES 7-9: re-storing an alpha preserves terminal status and operator
counts; sim errors are idempotent per sim; check storage replaces stale rows."""

from storage.store_alpha import store_alpha
from storage.store_checks import store_checks
from storage.store_sim import _record_error
from tests.test_storage.conftest import alpha_data, settings


def test_restore_preserves_submitted_status(conn):
    store_alpha(conn, "s1", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data("a1"))
    conn.execute("UPDATE alpha_results SET status='SUBMITTED' WHERE alpha_id='a1'")
    conn.commit()

    store_alpha(conn, "s1", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data("a1"))

    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "SUBMITTED"


def test_restore_preserves_rejected_status(conn):
    store_alpha(conn, "s1", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data("a1"))
    conn.execute("UPDATE alpha_results SET status='REJECTED' WHERE alpha_id='a1'")
    conn.commit()

    store_alpha(conn, "s1", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data("a1"))

    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "REJECTED"


def test_operator_counts_idempotent_on_restore(conn):
    expr = "rank(ts_delta(close, 5))"
    store_alpha(conn, "s1", expr, "USA", "TOP3000", 1, settings(), alpha_data("a1"))
    before = dict(conn.execute("SELECT operator, count FROM operator_usage").fetchall())
    assert before.get("rank") == 1

    store_alpha(conn, "s2", expr, "USA", "TOP3000", 1, settings(), alpha_data("a1"))
    after = dict(conn.execute("SELECT operator, count FROM operator_usage").fetchall())

    assert after == before  # re-store does not double count


def test_operator_counts_move_when_expression_changes(conn):
    store_alpha(conn, "s1", "rank(ts_delta(close, 5))", "USA", "TOP3000", 1, settings(), alpha_data("a1"))

    store_alpha(conn, "s1", "rank(close)", "USA", "TOP3000", 1, settings(), alpha_data("a1"))

    ops = dict(conn.execute("SELECT operator, count FROM operator_usage").fetchall())
    assert ops.get("rank") == 1
    assert "ts_delta" not in ops  # old expression's operators were subtracted


def test_record_error_is_idempotent_per_sim(conn):
    _record_error(conn, "rank(x)", "USA", "boom", settings(), "t1", sim_id="P1")
    _record_error(conn, "rank(x)", "USA", "boom again", settings(), "t2", sim_id="P1")

    rows = conn.execute("SELECT error_message, ts FROM sim_errors WHERE sim_id='P1'").fetchall()
    assert len(rows) == 1
    assert rows[0] == ("boom again", "t2")

    # Unknown sim_id keeps the append-only behavior (legacy path).
    _record_error(conn, "rank(x)", "USA", "no sim", settings(), "t3")
    _record_error(conn, "rank(x)", "USA", "no sim", settings(), "t4")
    assert conn.execute("SELECT COUNT(*) FROM sim_errors WHERE sim_id IS NULL").fetchone()[0] == 2


def test_store_checks_replaces_full_check_set(conn):
    store_checks(
        conn,
        "a1",
        [
            {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.65, "value": 2.0},
            {"name": "CONCENTRATED_WEIGHT", "result": "FAIL", "limit": 0.1, "value": 0.2},
        ],
    )

    result = store_checks(conn, "a1", [{"name": "LOW_SHARPE", "result": "PASS", "limit": 1.65, "value": 2.0}])

    names = {r[0] for r in conn.execute("SELECT check_name FROM submission_checks WHERE alpha_id='a1'")}
    assert names == {"LOW_SHARPE"}
    summary = conn.execute("SELECT pass_count, fail_count FROM alpha_check_summary WHERE alpha_id='a1'").fetchone()
    assert summary == (1, 0)
    assert result == {"pass": 1, "fail": 0, "warn": 0, "pend": 0}
