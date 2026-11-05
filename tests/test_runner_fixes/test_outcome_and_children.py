"""FIX 10: per-alpha outcome counting with sticky statuses."""

from runner.submit.outcome import update_alpha_status


def _seed_alpha(conn, alpha_id="a1", status="UNSUBMITTED"):
    conn.execute(
        "INSERT INTO alpha_results "
        "(alpha_id, region, universe, delay, neutralization, status, template) "
        "VALUES (?, 'USA', 'TOP3000', 1, 'MARKET', ?, 'T')",
        (alpha_id, status),
    )
    conn.commit()


def _counters(conn):
    return conn.execute("SELECT submitted, rejected, throttled FROM submission_outcomes").fetchone()


def test_outcome_counter_moves_once_per_alpha(conn):
    _seed_alpha(conn)

    update_alpha_status(conn, "a1", "FAIL:2")
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "REJECTED"
    assert _counters(conn) == (0, 1, 0)

    update_alpha_status(conn, "a1", "FAIL:2")  # same terminal state again
    assert _counters(conn) == (0, 1, 0)

    update_alpha_status(conn, "a1", "SUBMITTED")  # REJECTED -> SUBMITTED is allowed
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "SUBMITTED"
    assert _counters(conn) == (1, 1, 0)

    update_alpha_status(conn, "a1", "FAIL:1")  # never downgrade SUBMITTED
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "SUBMITTED"
    assert _counters(conn) == (1, 1, 0)


def test_already_submitted_maps_to_submitted(conn):
    _seed_alpha(conn)

    update_alpha_status(conn, "a1", "ALREADY_SUBMITTED")

    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "SUBMITTED"
    assert _counters(conn) == (1, 0, 0)


def test_transient_results_leave_status_alone(conn):
    _seed_alpha(conn)

    for result in ("VERIFY_FAILED", "CHECK_FAILED", "PASS_BUT_SUBMIT_FAILED", "PENDING"):
        update_alpha_status(conn, "a1", result)

    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='a1'").fetchone()[0] == "UNSUBMITTED"
    assert conn.execute("SELECT COUNT(*) FROM submission_outcomes").fetchone()[0] == 0
