"""Top-level check_and_submit flow + transient-vs-terminal status mapping.

The per-cell throttle state and the held-alpha queue live in
`runner.submit.throttle`, and the drain in `runner.submit.held`; both are
re-exported here so `from runner.submit.flow import ...` keeps working.
"""

from __future__ import annotations

import time  # noqa: F401 - tests patch flow.time to freeze the cooldown clock

from checker.auto_check_deferrals import _note_deferral
from core.log import get_file_logger
from core.scope import dispatch_block_reason, validate_expression
from runner.submit.held import DRAIN_PER_PASS, drain_held_queue  # noqa: F401
from runner.submit.outcome import update_alpha_status
from runner.submit.throttle import (  # noqa: F401
    QUEUE_LIMIT,
    THROTTLE_THRESHOLD,
    _held_alphas,
    _reset_throttle_state,
    _throttle_events,
    drain_held_alpha,
    in_cooldown,
    queue_held_alpha,
    record_throttle,
)
from runner.submit_checks import ensure_description, fallback_get_check, try_submit
from runner.submit_retry import _cooling_submit_rounds
from runner.verify_submit import verify_submission
from storage.store_checks import store_checks
from storage.submission_requests import begin_request, mark_verified, needs_reconciliation, record_response

clog = get_file_logger("check")


def _alpha_cell(conn, alpha_id):
    """Look up (region, universe, delay) for an alpha; None on miss."""
    row = conn.execute(
        "SELECT region, universe, delay FROM alpha_results WHERE alpha_id=?",
        (alpha_id,),
    ).fetchone()
    return tuple(row) if row else None


def _do_check_and_submit(session, conn, alpha_id):
    """Inner flow returning the outcome string. Status update is applied by caller."""
    clog.info("check_and_submit start: %s", alpha_id)

    if needs_reconciliation(conn, alpha_id):
        clog.info("%s: reconciling existing submission request with GET only", alpha_id)
        result = verify_submission(session, conn, alpha_id)
        if result == "SUBMITTED":
            mark_verified(conn, alpha_id)
        return result

    cell = _alpha_cell(conn, alpha_id)
    if cell is not None and in_cooldown(cell):
        queue_held_alpha(cell, alpha_id)
        clog.info("HELD: %s (cell %s in cooldown)", alpha_id, cell)
        return "HELD"

    # Step 1: Patch description (REQUIRED by BRAIN)
    ensure_description(session, alpha_id, conn)

    # Step 2: Try submit directly — let platform decide (regular + power pool).
    # Refuse to re-POST an alpha the platform has left undecided
    # `MAX_SUBMIT_ROUNDS` times. Both undecided paths write that count — a 403
    # carrying ERROR/PENDING and a `201` that never sets `dateSubmitted` — so
    # gating here bounds them together; reading it only on the 403 path left
    # the void-201 loop unbounded.
    #
    # The gate is a cooldown, not a one-way door: see
    # `SUBMIT_ROUND_COOLDOWN_SEC`. A count compared against a constant and
    # never lowered barred the alpha from submission for good, and the reason a
    # submit goes undecided is platform state — 32 alphas measured with a spent
    # count passed every check but an account-wide quota that had since reset.
    if rounds := _cooling_submit_rounds(conn, alpha_id):
        _note_deferral(conn, alpha_id)
        clog.warning("%s: %d undecided submit rounds — cooling down, not re-POSTing", alpha_id, rounds)
        return "CHECK_UNAVAILABLE_GIVEUP"
    if not begin_request(conn, alpha_id):
        # Another owner may have claimed it since the initial read.
        result = verify_submission(session, conn, alpha_id)
        if result == "SUBMITTED":
            mark_verified(conn, alpha_id)
        return result
    status_code, submit_result = try_submit(session, conn, alpha_id)
    record_response(conn, alpha_id, status_code)

    if status_code == 201:
        clog.info("Submit accepted (201): %s", alpha_id)
        result = verify_submission(session, conn, alpha_id)
        if result == "SUBMITTED":
            mark_verified(conn, alpha_id)
        return result
    if status_code == 429:
        clog.debug("Throttled, skip for now: %s", alpha_id)
        if cell is not None:
            record_throttle(cell)
        return "THROTTLED"
    if submit_result:
        clog.info("Submit rejected (%d): %s -> %s", status_code, alpha_id, submit_result)
        return submit_result

    # Fallback: GET /check (only for non-throttle failures)
    #
    # %s, not %d: `status_code` is None here whenever the POST never produced an
    # HTTP answer at all — both `check_via_submit` transport-failure returns are
    # `(None, None)` — and `%d` with None raises TypeError *inside* logging, so
    # the record is lost and a "--- Logging error ---" traceback lands in
    # stdout instead. Measured 2026-10-08 18:51: `omWlgVxk` took the read
    # timeout on the POST, then this line cost us the one log record that said
    # which path it was on.
    clog.debug("Fallback GET /check: %s (status=%s)", alpha_id, status_code)
    return fallback_get_check(session, conn, alpha_id, status_code)


API_BASE = "https://api.worldquantbrain.com"


def _scope_verdict(session, alpha_id):
    """Resolve this alpha's expression and validate its numeric leaves.

    Returns the `core.scope.validate_expression` verdict, or None when the
    expression cannot be read (in which case the guard abstains rather than
    inventing a failure).
    """
    try:
        resp = session.get(f"{API_BASE}/alphas/{alpha_id}", timeout=60)
        payload = resp.json()
    except Exception as e:
        clog.debug("scope guard could not read %s: %s", alpha_id, e)
        return None
    # Type-strict: a test double or an unexpected payload must make the guard
    # ABSTAIN, never fabricate a verdict out of a mock repr.
    if not isinstance(payload, dict):
        return None
    regular = payload.get("regular")
    if not isinstance(regular, dict):
        return None
    code = regular.get("code")
    if not isinstance(code, str) or not code.strip():
        return None
    return validate_expression(code)


def check_and_submit(session, conn, alpha_id):
    """Full flow: description -> submit -> verify. Updates alpha_results.status."""
    row = conn.execute("SELECT status FROM alpha_results WHERE alpha_id=?", (alpha_id,)).fetchone()
    if row and row[0] == "SUBMITTED":
        # Terminal: never re-POST an already-submitted alpha.
        clog.info("check_and_submit skip: %s already SUBMITTED", alpha_id)
        return "SUBMITTED"

    # Design 2026-11-05 (P0-1): semantic input validation before submission.
    # A risk/model/partition leaf, or an unresolvable one, must never reach the
    # POST. The refusal is recorded as a visible check row (and a summary, so
    # the selector stops re-picking it) rather than deleting or hiding anything.
    #
    # An alpha already carrying a submission request is in an UNCERTAIN state:
    # the only correct action there is reconciliation, and re-reading the
    # expression would add a network round trip without changing the decision.
    owned = False
    try:
        owned = conn.execute("SELECT COUNT(*) FROM submission_requests WHERE alpha_id=?", (alpha_id,)).fetchone()[0] > 0
    except Exception:
        owned = False
    verdict = None if owned else _scope_verdict(session, alpha_id)
    reason = dispatch_block_reason(verdict) if verdict else None
    if reason:
        clog.warning("scope-blocked %s: %s", alpha_id, reason)
        store_checks(conn, alpha_id, [{"name": "SCOPE_COMPLIANCE", "result": "FAIL", "value": None, "limit": None}])
        return "SCOPE_BLOCKED"

    result = _do_check_and_submit(session, conn, alpha_id)
    update_alpha_status(conn, alpha_id, result)
    if result == "SUBMITTED":
        # Mark the alpha as checked so even the status gate (or a manual
        # status flip) cannot make the selector pick it up again.
        store_checks(conn, alpha_id, [])
    return result
