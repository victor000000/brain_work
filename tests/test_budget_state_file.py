"""The on-disk budget-state file: corrupt, skewed, expired and atomic writes."""

import json
import time

from core.budget import BudgetState
from tests.test_budget_helpers import isolated_budget_state  # noqa: F401


def test_clock_skewed_persisted_window_is_ignored(monkeypatch, tmp_path):
    """A persisted reset_at far in the future (corrupt file / skewed clock)
    must not park the engine."""
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"exhausted": True, "reset_at": time.time() + 10**9, "last_reset_seconds": 10**9}))
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(path))
    state = BudgetState(persist=True)
    state.load_persisted_state()
    assert state.is_exhausted() is False


def test_corrupt_state_file_is_ignored(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not valid json")
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(path))
    state = BudgetState(persist=True)
    state.load_persisted_state()
    assert state.is_exhausted() is False


def test_expired_persisted_window_is_not_restored(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"exhausted": True, "reset_at": 1, "last_reset_seconds": 3600}))
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(path))
    state = BudgetState(persist=True)
    state.load_persisted_state()
    assert state.is_exhausted() is False


def test_non_persisting_instances_never_touch_disk(monkeypatch, tmp_path):
    path = tmp_path / "state.json"
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(path))
    state = BudgetState()  # persist=False (default)
    state.mark_exhausted(600)
    assert not path.exists()


def test_state_write_is_atomic_no_tmp_left_behind(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(tmp_path / "state.json"))
    state = BudgetState(persist=True)
    state.mark_exhausted(600)
    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []
