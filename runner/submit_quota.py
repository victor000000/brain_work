"""Telling an account-wide quota failure apart from a real rejection.

Split out of `runner/submit_checks.py`, which imports these names. A FAIL that
is about the account's allowance says nothing about the alpha, so it must never
retire one: the alpha is stored for visibility, deferred, and left eligible.
"""

from checker.auto_check_deferrals import _note_deferral
from core.log import get_file_logger
from storage.store_checks import ACCOUNT_WIDE_CHECKS, store_checks

clog = get_file_logger("check")


def failed_names(checks):
    """Every FAIL name in a check response."""
    return [c["name"] for c in checks if c.get("result") == "FAIL"]


def real_failures(checks):
    """FAIL names that are about the alpha rather than the account's quota."""
    return [n for n in failed_names(checks) if n not in ACCOUNT_WIDE_CHECKS]


def quota_blocked(conn, alpha_id, checks, fails):
    """Record a quota-only block and return its transient result.

    Deferring rather than retiring is the whole point: the quota resets, and an
    alpha discarded here is gone for good. `POWER_POOL_SUBMISSION` retired
    `d51Z6ZbE` (sharpe 2.40) and `vR2jeq9G` (1.93) as `REJECTED` on 2026-10-07
    before this existed.
    """
    store_checks(conn, alpha_id, checks, write_summary=False)
    _note_deferral(conn, alpha_id)
    clog.info("%s: blocked only by an account-wide quota %s — deferred", alpha_id, fails)
    return "QUOTA_BLOCKED"
