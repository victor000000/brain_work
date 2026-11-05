"""Auto-check top new alphas for submission after simulation runs.

The queue and its constants live in `checker.auto_check_queue`, the correlation
arms in `checker.auto_check_corr` and the per-alpha decision in
`checker.auto_check_alpha`; all are re-exported here.

`check_new_alphas` stays in this module rather than joining a sibling because
this is the patch point: the fetch/submit collaborators below are re-exported
from here (tests patch `auto_check.check_via_get` and friends) and so is the
run's clock (`auto_check.time`). It resolves them here and passes them in.
"""

import logging
import time

from checker.auto_check_alpha import CAP_REACHED, _check_alpha
from checker.auto_check_corr import _PREVIEW_CORRELATION_ARMS, CORRELATION_LIMIT, _preview_correlations  # noqa: F401
from checker.auto_check_queue import (  # noqa: F401
    CHECK_BATCH_LIMIT,
    CHECK_RUN_BUDGET_SEC,
    TERMINAL_STATUSES,
    _note_deferral,
    _select_candidates,
)
from checker.check_via_get import check_via_get
from core.log import get_file_logger
from runner.submit import check_and_submit

log = logging.getLogger("brain")
rlog = get_file_logger("runner")


def check_new_alphas(session, conn, limit=CHECK_BATCH_LIMIT):
    """Check top unchecked, eligible alphas. Auto-submit if pass.

    The queue query — eligible regions and sharpe floors, terminal-status and
    pv/option reachability filters, deferral ordering — is `_select_candidates`
    in `checker.auto_check_queue`, which documents each rule.
    """
    top_new = _select_candidates(conn, limit)

    if not top_new:
        rlog.debug("No new alphas to check for submission")
        return

    rlog.info("Checking %d new alphas for submission...", len(top_new))
    log.info("Checking %d new alphas for submission...", len(top_new))
    started = time.monotonic()
    for done, (aid, sh) in enumerate(top_new):
        if time.monotonic() - started >= CHECK_RUN_BUDGET_SEC:
            rlog.warning(
                "Check run hit its %ds budget after %d/%d alphas — the rest go to the next run",
                CHECK_RUN_BUDGET_SEC,
                done,
                len(top_new),
            )
            break
        time.sleep(0.5)
        outcome = _check_alpha(
            session,
            conn,
            aid,
            sh,
            check_via_get=check_via_get,
            check_and_submit=check_and_submit,
        )
        if outcome == CAP_REACHED:
            # Nothing this run decides can be submitted until the boundary, and
            # the cap *masks* the rest of the check set — during the capped
            # hours a preview reports `REGULAR_SUBMISSION` alone even for alphas
            # that fail three checks (measured 2026-10-07: seven alphas went
            # from "one failure" to SELF_CORRELATION 0.77 / PROD_CORRELATION
            # 0.84-0.87 / LOW_2Y_SHARPE 0.25-1.15 once the cap lifted). So the
            # remaining alphas would be deferred on no evidence at the cost of
            # two endpoints' worth of rate limit each. Stop, and let the next
            # run past the reset do the work.
            rlog.warning(
                "Check run stopped at %d/%d: the day's submission cap is spent, and it masks the rest of the check set",
                done + 1,
                len(top_new),
            )
            log.warning("Submission cap spent — check run stopping early")
            break
