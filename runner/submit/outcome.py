"""Persist terminal-status outcomes to alpha_results + submission_outcomes."""

_OUTCOME_COLUMN = {"SUBMITTED": "submitted", "REJECTED": "rejected", "THROTTLED": "throttled"}


def _result_to_status(result):
    """Map check_and_submit result string to a terminal status, or None if transient."""
    if result in ("SUBMITTED", "ALREADY_SUBMITTED"):
        return "SUBMITTED"
    if result == "THROTTLED":
        return "THROTTLED"
    if result == "HELD":
        return None
    if isinstance(result, str) and result.startswith("FAIL:"):
        return "REJECTED"
    return None


def _record_outcome_statements(conn, alpha_id, status):
    """Counter SQL without its own transaction (caller owns commit/rollback)."""
    if status not in _OUTCOME_COLUMN:
        return
    row = conn.execute(
        "SELECT template, region, universe, delay, neutralization FROM alpha_results WHERE alpha_id = ?",
        (alpha_id,),
    ).fetchone()
    if not row or row[0] is None:
        return
    col = _OUTCOME_COLUMN[status]
    conn.execute(
        f"INSERT OR IGNORE INTO submission_outcomes "
        f"(template, region, universe, delay, neutralization, {col}) "
        f"VALUES (?, ?, ?, ?, ?, 0)",
        row,
    )
    conn.execute(
        f"UPDATE submission_outcomes SET {col} = {col} + 1 "
        f"WHERE template=? AND region=? AND universe=? AND delay=? AND neutralization=?",
        row,
    )


def _record_outcome(conn, alpha_id, status):
    """Increment submission_outcomes counter for the alpha's full cell.

    Low-level primitive: bumps the counter by one per call. It is wrapped in a
    single transaction; callers that must count an alpha only once (the live
    check_and_submit path) go through update_alpha_status, which only records
    an outcome on a real status transition.
    """
    with conn:
        _record_outcome_statements(conn, alpha_id, status)


def update_alpha_status(conn, alpha_id, result):
    """Map check_and_submit result to alpha_results.status.

    Terminal outcomes (SUBMITTED, REJECTED, THROTTLED) get persisted; the
    remaining outcomes are transient — leave the row as UNSUBMITTED so it
    becomes eligible for retry on the next check pass.

    Guarantees:
      - SUBMITTED is sticky: a later FAIL/THROTTLED never downgrades it.
      - REJECTED is sticky except for an explicit SUBMITTED outcome.
      - The status UPDATE and the submission_outcomes counter share one
        transaction, and the counter only moves when the status actually
        transitions (per-alpha, not per-event).
    """
    new_status = _result_to_status(result)
    if new_status is None:
        return
    with conn:
        row = conn.execute("SELECT status FROM alpha_results WHERE alpha_id=?", (alpha_id,)).fetchone()
        current = row[0] if row else None
        if current == "SUBMITTED":
            return
        if current == "REJECTED" and new_status != "SUBMITTED":
            return
        if current == new_status:
            # Same terminal state observed again (e.g. the nth 429 for an
            # already-THROTTLED alpha): do not double-count.
            return
        conn.execute("UPDATE alpha_results SET status=? WHERE alpha_id=?", (new_status, alpha_id))
        _record_outcome_statements(conn, alpha_id, new_status)
