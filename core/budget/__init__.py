"""Budget tracking — package layout.

Public API kept stable:
  BudgetState, get_state, set_state             — singleton state.
  BUDGET_FLOOR                                  — exhaustion threshold.
  is_exhausted(), seconds_until_reset(),
  mark_exhausted(reset_seconds)                 — module-level proxies.
  update_from_headers(headers)                  — passive header reader.
  read_remaining(resp)                          — parsed X-Ratelimit-Remaining.
  check_budget(resp)                            — header reader + log + exhaust.
"""

from core.budget.headers import check_budget, read_remaining, update_from_headers
from core.budget.proxies import is_exhausted, mark_exhausted, seconds_until_reset, submission_capacity
from core.budget.state import BUDGET_FLOOR, BudgetState, get_state, set_state

__all__ = [
    "BUDGET_FLOOR",
    "BudgetState",
    "check_budget",
    "get_state",
    "is_exhausted",
    "mark_exhausted",
    "read_remaining",
    "seconds_until_reset",
    "set_state",
    "submission_capacity",
    "update_from_headers",
]
