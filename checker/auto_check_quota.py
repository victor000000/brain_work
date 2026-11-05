"""An account-wide quota seen in the preview, rather than at submit time.

Split out of `checker/auto_check_alpha.py`, which imports both names.
"""

from checker.auto_check_queue import _note_deferral
from storage.store_checks import ACCOUNT_WIDE_CHECKS


def quota_only(fails):
    """True when every FAIL is the account's allowance, not the alpha's."""
    return bool(fails) and set(fails) <= ACCOUNT_WIDE_CHECKS


def defer_for_quota(conn, alpha_id, fails):
    """Defer an alpha blocked only by a quota; report whether to stop the run.

    A quota fails on *every* alpha while the allowance is spent, so retiring
    here discards submission-ready alphas permanently — 51 were lost within an
    hour of the cap being reached on 2026-10-06. `store_checks` already leaves
    such an alpha out of the summary so it stays eligible, but nothing deferred
    it, so it kept its sharpe rank, headed every run, and paid a 45s preview
    per cycle to be told the same thing; `POWER_POOL_SUBMISSION` did that to
    the cap-blocked HKG alphas on 2026-10-07.

    Only `REGULAR_SUBMISSION` also stops the run. It is the account's cap and
    every later alpha would fail it identically, whereas the power pool gates
    only the alphas that match it — `omWqeawm` took a real correlation verdict
    while four neighbours were `QUOTA_BLOCKED`, so halting on it would deny the
    rest theirs.
    """
    _note_deferral(conn, alpha_id)
    return fails == ["REGULAR_SUBMISSION"]
