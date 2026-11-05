"""Check and auto-submit alphas via BRAIN platform — package layout.

Flow: patch description -> POST /submit -> verify.
Skip correlation gate — let the platform decide. Power Pool accepts
alphas that fail regular correlation checks.

After the flow completes, alpha_results.status is updated to reflect the
terminal outcome (SUBMITTED / REJECTED / THROTTLED). Transient/unknown
outcomes (NOT_SUBMITTED, VERIFY_FAILED, CHECK_FAILED, PASS_BUT_SUBMIT_FAILED)
leave status as UNSUBMITTED so the alpha is eligible for retry next pass.

Public API:
  check_and_submit(session, conn, alpha_id)  — run full flow.
"""

from runner.submit.flow import check_and_submit
from runner.submit.outcome import (
    _OUTCOME_COLUMN,
    _record_outcome,
    _result_to_status,
)
from runner.submit.outcome import update_alpha_status as _update_alpha_status

# Tests reach into the underscore-prefixed helpers for unit-level coverage;
# re-export them here so external imports keep working post-split.
__all__ = [
    "_OUTCOME_COLUMN",
    "_record_outcome",
    "_result_to_status",
    "_update_alpha_status",
    "check_and_submit",
]
