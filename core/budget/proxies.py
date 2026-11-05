"""Module-level proxies that delegate to the active BudgetState singleton.

Kept as separate top-level functions for backwards compatibility with call
sites like `budget.is_exhausted()` and `budget.mark_exhausted(reset)`.
"""

from core.budget.state import get_state


def is_exhausted():
    return get_state().is_exhausted()


def seconds_until_reset():
    return get_state().seconds_until_reset()


def mark_exhausted(reset_seconds):
    return get_state().mark_exhausted(reset_seconds)


def submission_capacity(maximum):
    return get_state().submission_capacity(maximum)
