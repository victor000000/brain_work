"""Store submission check results to DB.

The per-row writes live in `storage.store_checks_rows` and the polish queue in
`storage.store_checks_polish`; both are re-exported here so
`from storage.store_checks import ...` keeps resolving for every caller.
"""

import logging
import time

from core.log import get_file_logger
from storage.store_checks_polish import POLISH_MIN_PASSES, _enqueue_polish_candidate
from storage.store_checks_rows import _record_check_rows

log = logging.getLogger("brain")
clog = get_file_logger("check")

# Checks that fail on the account's allowance rather than on anything about the
# alpha, and so must never retire one. `REGULAR_SUBMISSION` reads `limit=4
# val=4` and `POWER_POOL_SUBMISSION` reads `limit=1 val=1` — the latter was
# found on 2026-10-07, when it retired `d51Z6ZbE` (sharpe 2.40) as `REJECTED`
# for a spent power-pool quota.
ACCOUNT_WIDE_CHECKS = frozenset({"REGULAR_SUBMISSION", "POWER_POOL_SUBMISSION"})


def store_checks(conn, alpha_id, checks, write_summary=True):
    """Save check results. Returns {pass, fail, warn, pend} counts.

    The stored set is replaced wholesale: check rows for names absent from the
    newest response are deleted, so submission_checks and alpha_check_summary
    can never disagree about which checks the alpha actually has.

    `write_summary=False` stores the check rows for visibility and removes any
    previous `alpha_check_summary` row, which the auto-checker uses as its
    "already checked" filter. Transient outcomes (the platform failing to run
    a check, or checks still pending) must use it, or an older summary excludes
    the alpha from every future pass despite the newest outcome being undecided.
    """
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    current_names, pass_count, fail_count, warn_count, pend_count = _record_check_rows(conn, alpha_id, checks, now)

    # Drop stale rows from a previous (larger) check response.
    existing = {
        r[0] for r in conn.execute("SELECT check_name FROM submission_checks WHERE alpha_id=?", (alpha_id,)).fetchall()
    }
    for stale in existing - current_names:
        conn.execute("DELETE FROM submission_checks WHERE alpha_id=? AND check_name=?", (alpha_id, stale))

    # A quota is a property of the account, not of the alpha: once the period's
    # allowance is spent the check fails on *every* alpha. Recording that as a
    # decided check excludes the alpha from every later pass —
    # `alpha_check_summary` is the auto-checker's "already checked" filter — so
    # an account-wide condition would permanently retire submission-ready
    # alphas. Measured 2026-10-06: 51 alphas whose only failing check was the
    # cap were retired within an hour of it being reached. Store the rows for
    # visibility, leave the alpha queued: the same contract `write_summary=False`
    # exists for. Callers that reach the cap before previewing
    # (checker/auto_check_alpha) never get here at all.
    failed = {ch["name"] for ch in checks if ch.get("result") == "FAIL"}
    if failed and failed <= ACCOUNT_WIDE_CHECKS:
        write_summary = False
        clog.info("%s: only an account-wide quota failed %s — no summary, stays queued", alpha_id, sorted(failed))

    if write_summary:
        conn.execute(
            "INSERT OR REPLACE INTO alpha_check_summary VALUES (?,?,?,?,?,?)",
            (alpha_id, pass_count, fail_count, warn_count, pend_count, now),
        )
        if fail_count == 1 and pass_count >= POLISH_MIN_PASSES:
            _enqueue_polish_candidate(conn, alpha_id, now)
    else:
        # The newest response supersedes a previous decision. Merely skipping
        # INSERT leaves an old summary behind and permanently hides an alpha
        # whose latest ERROR/PENDING or quota outcome is explicitly retryable.
        # Historical failures remain in check_failures; terminal status and
        # the independent deferral/cooldown state are left intact.
        conn.execute("DELETE FROM alpha_check_summary WHERE alpha_id=?", (alpha_id,))
    conn.commit()

    clog.info("%s: P=%d F=%d W=%d Pend=%d", alpha_id, pass_count, fail_count, warn_count, pend_count)
    return {"pass": pass_count, "fail": fail_count, "warn": warn_count, "pend": pend_count}
