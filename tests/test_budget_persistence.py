"""Cross-process persistence: exhaustion windows are shared and never clobbered."""

from core.budget import BudgetState
from tests.test_budget_helpers import isolated_budget_state  # noqa: F401


def test_persisted_exhaustion_survives_a_new_process_state(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(tmp_path / "state.json"))
    first = BudgetState(persist=True)
    first.mark_exhausted(600)

    second = BudgetState(persist=True)
    second.load_persisted_state()
    assert second.is_exhausted() is True
    assert second.seconds_until_reset() > 0


def test_persisted_exhaustion_is_not_clobbered_by_another_process(monkeypatch, tmp_path):
    """A second process writing its own (healthy) state must not erase a live
    exhaustion window: a restart would then treat the budget as healthy."""
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(tmp_path / "state.json"))
    first = BudgetState(persist=True)
    first.mark_exhausted(3600)

    second = BudgetState(persist=True)  # fresh process, never saw the 429
    second.note_remaining(4999)  # e.g. a healthy header on a later call
    assert second.is_exhausted() is True  # it adopts the shared window

    third = BudgetState(persist=True)  # a restart after both wrote
    third.load_persisted_state()
    assert third.is_exhausted() is True
    assert third.seconds_until_reset() > 3000


def test_a_shorter_window_cannot_shorten_a_shared_longer_one(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(tmp_path / "state.json"))
    daily = BudgetState(persist=True)
    daily.mark_exhausted(3600)

    transient = BudgetState(persist=True)  # only saw a 60s 429
    transient.mark_exhausted(60)

    restart = BudgetState(persist=True)
    restart.load_persisted_state()
    assert restart.is_exhausted() is True
    assert restart.seconds_until_reset() > 3000


def test_reset_still_clears_a_shared_window(monkeypatch, tmp_path):
    """An operator reset is deliberate: it must clear exhaustion for everyone."""
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(tmp_path / "state.json"))
    first = BudgetState(persist=True)
    first.mark_exhausted(3600)
    first.reset()

    restart = BudgetState(persist=True)
    restart.load_persisted_state()
    assert restart.is_exhausted() is False
