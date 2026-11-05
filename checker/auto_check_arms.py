"""Resolve an alpha's correlation arms from the preview.

Split out of `checker/auto_check_alpha.py`. The two endpoint fetchers are gone
from the check path entirely, not merely unused: with nothing polling them,
keeping them as parameters only invited a future edit to start polling again.
"""

from checker.auto_check_corr import _preview_correlations
from core.log import get_file_logger

rlog = get_file_logger("runner")

# An arm the preview did not decide. Deliberately not `FETCH_ERROR`: nothing
# was fetched, and the caller's job is now to submit and let the platform
# answer. `_corr_passes` fails closed on any non-numeric value, so this takes
# the same "undecided, submit anyway" path the fetchers' errors took.
UNDECIDED = "UNDECIDED"


def resolve_correlations(preview):
    """`{arm: value}` for both correlation arms, from the preview alone.

    The two endpoint polls are gone. They returned nothing for hours at a
    time — 94% of alphas arrived on 2026-10-07 with both arms undecided — and
    cost up to 120s each, which put a check run at 92s per alpha and capped it
    at 14 of 32 while 95% of generated alphas were never checked at all.

    They used to protect the submission budget: a numeric value over the line
    meant recording a FAIL instead of spending an attempt. That protection is
    gone, because a submission failing correlation returns 403 and spends
    nothing — so in no branch did the poll change the outcome. It did not save
    a POST either: an undecided alpha is submitted regardless, and the submit's
    403 returns the same numeric verdict, which is how `omWqeawm` got
    `PROD_CORRELATION val=0.8502` recorded. Removing them strictly reduces
    requests and time.
    """
    corr = _preview_correlations(preview)
    for arm in ("prod", "self"):
        corr.setdefault(arm, UNDECIDED)
    return corr
