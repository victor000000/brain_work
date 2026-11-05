"""Helper functions for alpha submission check flow.

The retry bookkeeping and the description patch live in `submit_retry` and
`submit_desc`; they are re-exported here so `from runner.submit_checks import
...` keeps working for every caller.
"""

import logging

from checker.auto_check_deferrals import _note_deferral
from checker.check_via_get import check_via_get
from checker.check_via_submit import check_via_submit
from core.log import get_file_logger
from runner.submit_desc import ensure_description  # noqa: F401
from runner.submit_quota import failed_names, quota_blocked, real_failures
from runner.submit_retry import MAX_SUBMIT_ROUNDS, _increment_retry_count
from storage.store_checks import store_checks

log = logging.getLogger("brain")
clog = get_file_logger("check")


def try_submit(session, conn, alpha_id):
    """Attempt submit and handle 403/other. Returns (status_code, result_str or None)."""
    status_code, checks = check_via_submit(session, alpha_id)

    if status_code == 403 and checks:
        # The platform tells us the alpha is already submitted; that is a
        # success, never a rejection.
        if any(c.get("name") == "ALREADY_SUBMITTED" for c in checks):
            store_checks(conn, alpha_id, checks)
            clog.info("%s: ALREADY_SUBMITTED", alpha_id)
            return status_code, "ALREADY_SUBMITTED"
        # Only a genuine FAIL is a rejection. An ERROR is the platform failing
        # to run a check (CLUSTER_TEST errors account-wide, observed 75/75 on
        # 2026-10-03) and PENDING means still computing — neither says anything
        # about the alpha, so the alpha must stay retry-eligible.
        fails, real = failed_names(checks), real_failures(checks)
        if real:
            store_checks(conn, alpha_id, checks)
            clog.info("%s: REJECTED F=%d -- %s", alpha_id, len(real), real)
            return status_code, f"FAIL:{len(real)}"
        if fails:
            return status_code, quota_blocked(conn, alpha_id, checks, fails)
        # Not decided: store the rows for visibility but no summary, so the
        # alpha stays in the auto-checker's retry queue. The count is what
        # `runner.submit.flow` gates the next POST on.
        rounds = _increment_retry_count(conn, alpha_id)
        store_checks(conn, alpha_id, checks, write_summary=False)
        _note_deferral(conn, alpha_id)
        blocked = [f"{c.get('name')}={c.get('result')}" for c in checks if c.get("result") in ("ERROR", "PENDING")]
        clog.warning(
            "%s: submit blocked by errored/pending checks (round %d/%d): %s",
            alpha_id,
            rounds,
            MAX_SUBMIT_ROUNDS,
            blocked,
        )
        return status_code, "CHECK_UNAVAILABLE"

    if status_code != 201:
        return status_code, None  # caller should fallback

    return status_code, None


def _undecided(conn, alpha_id):
    """Record a submit/check round we could not decide, and say so.

    A GET that errors, times out or answers non-200 leaves us knowing exactly
    as much as the POST did — nothing — so the deferral must be written here.
    It was not: both `CHECK_FAILED` returns skipped it, and `CHECK_FAILED` is
    not in `checker.auto_check_alpha.UNDECIDED_OUTCOMES` either, so `_check_alpha`
    deleted whatever deferral the alpha already had. The alpha therefore kept
    its sharpe rank, headed the next check run and spent another 90s preview
    and 45s submit on a platform that was timing out — the same unbounded loop
    `verify_submit._count_undecided` documents for `VERIFY_FAILED`. Measured
    2026-10-08 18:51: `omWlgVxk` (sharpe 1.70) went CHECK_FAILED on a read
    timeout with its `RETRY_ATTEMPT`/deferral accounting left at zero.

    Deliberately does NOT call `_increment_retry_count`: that count is what
    `_cooling_submit_rounds` bars the next POST on, and a failure on the GET is
    not evidence that a POST would be left undecided. The deferral alone is the
    queue-ordering signal.
    """
    _note_deferral(conn, alpha_id)
    return "CHECK_FAILED"


def fallback_get_check(session, conn, alpha_id, status_code):
    """Fallback: GET /check when submit didn't return 201 or 403.

    Deliberately does NOT write alpha_check_summary: this path runs on
    transient submit failures (429/5xx/timeouts) where the outcome is not yet
    known, and a summary row would permanently exclude the alpha from future
    check passes. Definitive failures still map to REJECTED via the returned
    FAIL count; everything else stays status-UNSUBMITTED and retry-eligible.
    """
    clog.debug("%s: submit HTTP %s, fallback to GET", alpha_id, status_code)
    checks = check_via_get(session, alpha_id)
    if checks:
        real = real_failures(checks)
        if real:
            clog.info("%s: GET check shows %d fail(s): %s", alpha_id, len(real), real)
            return f"FAIL:{len(real)}"
        if failed_names(checks):
            return quota_blocked(conn, alpha_id, checks, failed_names(checks))
        # ERROR/PENDING checks are not failures — see try_submit.
        if any(c.get("result") in ("ERROR", "PENDING") for c in checks):
            clog.warning("%s: GET check blocked by errored/pending checks", alpha_id)
            return _undecided(conn, alpha_id)
        return "PASS_BUT_SUBMIT_FAILED"
    # `None` means the GET itself produced no verdict — a transport error, a
    # non-200, or its own 90s deadline. Nothing about the alpha was learned.
    return _undecided(conn, alpha_id)
