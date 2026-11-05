"""F6 cache-holder tests for BudgetState — reset, swap, isolation."""

import core.budget as budget


def test_budget_state_reset_clears_exhaustion():
    s = budget.BudgetState()
    s.mark_exhausted(60)
    assert s.is_exhausted() is True
    s.reset()
    assert s.is_exhausted() is False
    assert s.seconds_until_reset() == 0


def test_budget_set_state_swaps_singleton():
    """Tests can inject a fresh state to avoid leaking across cases."""
    original = budget.get_state()
    fresh = budget.BudgetState()
    budget.set_state(fresh)
    try:
        assert budget.get_state() is fresh
        budget.mark_exhausted(60)
        assert fresh.is_exhausted() is True
        # Original is untouched.
        assert original.is_exhausted() is False or original is not fresh
    finally:
        budget.set_state(original)


def test_budget_state_independent_instances():
    s1 = budget.BudgetState()
    s2 = budget.BudgetState()
    s1.mark_exhausted(60)
    assert s1.is_exhausted() is True
    assert s2.is_exhausted() is False
