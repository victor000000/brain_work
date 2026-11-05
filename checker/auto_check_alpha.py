"""The per-alpha check: preview gate, correlation gate, then submit.

Split out of `checker/auto_check.py`, which re-exports the name and passes its
fetch/submit collaborators in — they are that module's monkeypatch surface.
"""

import logging

from checker.auto_check_arms import resolve_correlations
from checker.auto_check_corr import CORRELATION_LIMIT
from checker.auto_check_quota import defer_for_quota, quota_only
from core.api import _corr_passes
from core.log import get_file_logger
from storage.store_checks import store_checks
from storage.submission_requests import needs_reconciliation

log = logging.getLogger("brain")
rlog = get_file_logger("runner")

# Returned when the preview shows the submission cap alone. The caller stops
# the run on it: see `check_new_alphas`.
CAP_REACHED = "CAP_REACHED"

# Outcomes that mean we still know nothing about this alpha. A deferral
# records exactly that state, so these must not clear it.
#
# Clearing it on this path is what kept the queue backoff inert: `flow.py`
# calls `_note_deferral` on every undecided submit round, but the DELETE below
# used to run *before* the submit, resetting the count to zero first — so the
# 28-failure alpha re-entered every run as a first-time offender and the count
# the selector reads could never reach its threshold.
# `VERIFY_FAILED` belongs here for the same reason: it means a `201` came back
# and the confirming GET did not, so the submission may or may not have
# happened. Clearing the deferral on it also cleared the count's only visible
# effect, because the count and the deferral are written together — see
# `runner.verify_submit._count_undecided`.
#
# The three that were still missing each write a deferral higher up and then
# had it deleted here, which is the same defect one layer down — a deferral
# whose only reader is this DELETE is a count that never reaches the selector:
#   PENDING        — a `201` whose `dateSubmitted` never landed, counted and
#                    deferred by `verify_submit._count_undecided`.
#   CHECK_FAILED   — the fallback GET produced no verdict (transport error,
#                    non-200, or its own deadline), deferred by
#                    `runner.submit_checks._undecided`.
#   QUOTA_BLOCKED  — the platform refused on the account's allowance, deferred
#                    by `runner.submit_quota.quota_blocked`; a quota says
#                    nothing about the alpha and it resets.
UNDECIDED_OUTCOMES = frozenset(
    {
        "CHECK_UNAVAILABLE",
        "CHECK_UNAVAILABLE_GIVEUP",
        "THROTTLED",
        "HELD",
        "VERIFY_FAILED",
        "PENDING",
        "CHECK_FAILED",
        "QUOTA_BLOCKED",
    }
)


def _check_alpha(session, conn, aid, sh, *, check_via_get, check_and_submit):
    """Decide one alpha: preview, correlation, then submit it if it passes.

    The four collaborators are parameters rather than imports so that
    `checker.auto_check` — where tests and callers patch them — stays their
    patch point. A gate that cannot be decided returns without submitting.
    """
    if needs_reconciliation(conn, aid):
        result = check_and_submit(session, conn, aid)
        rlog.info("  %s (sh=%.2f): existing request reconciliation: %s", aid, sh, result)
        return

    # Preview first: the platform computes nearly the whole check set on
    # GET /check without spending a submission. Only alphas whose preview
    # shows no FAIL are worth a submission attempt; the rest are recorded
    # (summary written, so the queue drains) and skipped.
    preview = check_via_get(session, aid)
    if preview is not None:
        fails = [c["name"] for c in preview if c.get("result") == "FAIL"]
        if fails:
            # A quota is not a property of this alpha; see `auto_check_quota`
            # for why it defers rather than retires.
            if quota_only(fails):
                rlog.info("  %s (sh=%.2f): account-wide quota fails %s — deferring", aid, sh, fails)
                if defer_for_quota(conn, aid, fails):
                    return CAP_REACHED
            store_checks(conn, aid, preview)
            rlog.info("  %s (sh=%.2f): PREVIEW-FAIL %s — not submitted", aid, sh, fails)
            log.info("  %s (sh=%.2f): preview failed %s", aid, sh, fails)
            return

    # The on-demand endpoints answer ahead of the submit, but the platform is
    # the authority: it recomputes correlation at submit time. Preserve an
    # explicit native PASS even above our scalar limit: XgRn2YRl passed native
    # PROD_CORRELATION at0.7331 on2026-10-19. Do not invent a FAIL by discarding
    # the verdict. Explicit FAILs were already handled above. An arm it
    # cannot compute comes back ERROR/PENDING, which `try_submit` maps to a
    # transient result — so an undecided arm cannot burn the alpha, and
    # deferring on it only guarantees the opportunity is lost. Measured
    # 2026-10-07: deferring blocked 180 alphas over 4.5h, and A1vlJZgQ
    # (sharpe 2.62) was accepted the moment it was submitted by hand.
    corr = resolve_correlations(preview)
    rlog.info("  %s correlation: prod=%s self=%s", aid, corr["prod"], corr["self"])
    passed_arms = {
        (ch.get("name") or "").removesuffix("_CORRELATION").lower()
        for ch in preview or []
        if ch.get("result") == "PASS" and ch.get("name") in ("PROD_CORRELATION", "SELF_CORRELATION")
    }
    corr_ok = all(arm in passed_arms or _corr_passes(v, CORRELATION_LIMIT) for arm, v in corr.items())
    if not corr_ok:
        over = {
            k: v
            for k, v in corr.items()
            if k not in passed_arms
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
            and v >= CORRELATION_LIMIT
        }
        if over:
            # Replace any same-named row the preview already carried rather
            # than appending a second one: `store_checks` keys on
            # (alpha_id, check_name), so a duplicate would silently depend
            # on iteration order.
            failed_names = {f"{k.upper()}_CORRELATION" for k in over}
            rows = [c for c in (preview or []) if (c.get("name") or "").upper() not in failed_names]
            rows += [
                {"name": f"{k.upper()}_CORRELATION", "result": "FAIL", "limit": CORRELATION_LIMIT, "value": v}
                for k, v in over.items()
            ]
            store_checks(conn, aid, rows)
            rlog.info("  %s (sh=%.2f): CORRELATION-FAIL %s — not submitted", aid, sh, over)
            return
        rlog.info("  %s (sh=%.2f): correlation undecided %s — submitting anyway", aid, sh, corr)

    result = check_and_submit(session, conn, aid)
    rlog.info("  %s (sh=%.2f): %s", aid, sh, result)
    log.info("  %s (sh=%.2f): %s", aid, sh, result)

    # The deferral is cleared once we have learned something — a submission, a
    # rejection, a decided check — so the alpha stops sorting last. It is kept
    # when the outcome is undecided, because then the deferral is still an
    # accurate description of what we know, and its `attempts` is the count
    # `_select_candidates` backs off on.
    if result not in UNDECIDED_OUTCOMES:
        conn.execute("DELETE FROM check_deferrals WHERE alpha_id=?", (aid,))
        conn.commit()

    if result == "SUBMITTED":
        rlog.warning("ALPHA SUBMITTED: %s sharpe=%.2f", aid, sh)
        log.warning("ALPHA SUBMITTED: %s sharpe=%.2f", aid, sh)
