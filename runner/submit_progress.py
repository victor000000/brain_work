"""Observe an existing asynchronous submission; never initiate another one."""

from dataclasses import dataclass

from core.log import get_file_logger
from runner.http_retry import parse_retry_after
from runner.submit_quota import failed_names, quota_blocked, real_failures
from storage.store_checks import store_checks
from storage.submission_requests import needs_reconciliation, record_response

clog = get_file_logger("check")
API = "https://api.worldquantbrain.com"


@dataclass(frozen=True)
class SubmissionProgress:
    outcome: str | None = None
    retry_after: float | None = None
    unavailable: bool = False


def get_submission_progress(session, conn, alpha_id, timeout):
    """Only an explicit403 with native FAIL checks decides a rejection.

    A200 progress response is not acceptance: the caller must still observe
    dateSubmitted. A404 is an expired/missing observer, not proof of rejection.
    The latter must never release an uncertain request for another POST.
    """
    try:
        resp = session.get(f"{API}/alphas/{alpha_id}/submit", timeout=timeout)
        retry = parse_retry_after(resp.headers)
        clog.debug("Submission progress %s: HTTP%d retry=%s", alpha_id, resp.status_code, retry)
        if resp.status_code == 404:
            return SubmissionProgress(unavailable=True)
        if resp.status_code != 403:
            return SubmissionProgress(retry_after=retry)
        body = resp.json()
        block = body.get("is") if isinstance(body, dict) else None
        checks = block.get("checks") if isinstance(block, dict) else None
        if not isinstance(checks, list) or not all(
            isinstance(ch, dict) and isinstance(ch.get("name"), str) for ch in checks
        ):
            return SubmissionProgress()
    except Exception as error:
        clog.warning("Submission progress %s unavailable: %s", alpha_id, error)
        return SubmissionProgress()

    if any(ch["name"] == "ALREADY_SUBMITTED" for ch in checks):
        return SubmissionProgress()
    fails = failed_names(checks)
    if not fails:
        # ERROR/PENDING do not establish a rejection, even on an HTTP403.
        return SubmissionProgress()
    owned = needs_reconciliation(conn, alpha_id)
    if owned:
        state = conn.execute("SELECT state FROM submission_requests WHERE alpha_id=?", (alpha_id,)).fetchone()[0]
        if state == "VERIFIED":
            # An earlier actual receipt cannot be undone by a stale observer.
            return SubmissionProgress()
    real = real_failures(checks)
    if real:
        store_checks(conn, alpha_id, checks)
        outcome = f"FAIL:{len(real)}"
        clog.info("%s: native asynchronous submission rejected: %s", alpha_id, real)
    else:
        outcome = quota_blocked(conn, alpha_id, checks, fails)
    if owned:
        # Persist the decided checks before releasing the rejected request.
        record_response(conn, alpha_id, 403)
    return SubmissionProgress(outcome=outcome)
