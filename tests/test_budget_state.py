"""BudgetState exhausted-window handling, including malformed reset values."""

from core.budget import BudgetState, get_state, set_state, update_from_headers
from tests.test_budget_helpers import isolated_budget_state  # noqa: F401


def test_mark_exhausted_does_not_shorten_a_longer_window():
    state = BudgetState()
    state.mark_exhausted(3600)
    state.mark_exhausted(60)  # transient 429 must not shorten the daily window
    assert state.is_exhausted() is True
    assert state.seconds_until_reset() > 3000
    assert state.last_reset_seconds == 3600


def test_mark_exhausted_extends_a_shorter_window():
    state = BudgetState()
    state.mark_exhausted(60)
    state.mark_exhausted(600)
    assert state.seconds_until_reset() > 500


def test_mark_exhausted_keeps_floor():
    state = BudgetState()
    state.mark_exhausted(1)
    assert state.last_reset_seconds >= 30


def test_mark_exhausted_survives_malformed_reset_values():
    """A garbage reset header must not raise or park the engine forever."""
    state = BudgetState()
    for bad in ("inf", "-inf", "nan", "?", None, "", 1e300, "1e300"):
        state = BudgetState()
        state.mark_exhausted(bad)  # must not raise
        assert state.is_exhausted() is True
        assert 0 < state.seconds_until_reset() <= 24 * 3600 + 1


def test_update_from_headers_survives_infinite_reset(monkeypatch, tmp_path):
    """X-Ratelimit-Reset: inf used to raise OverflowError out of the submit path."""
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(tmp_path / "state.json"))
    original = get_state()
    set_state(BudgetState(persist=True))
    try:
        update_from_headers({"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": "inf"})
        assert get_state().is_exhausted() is True
        assert get_state().seconds_until_reset() <= 24 * 3600 + 1
    finally:
        set_state(original)
