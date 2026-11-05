"""Shared fixture for the budget-state test modules."""

import pytest

from core.budget import BudgetState, get_state, set_state


@pytest.fixture(autouse=True)
def isolated_budget_state():
    """Swap in a throwaway (non-persisting) state so tests neither leak
    exhaustion into each other nor write the shared state file."""
    original = get_state()
    set_state(BudgetState())
    yield
    set_state(original)
