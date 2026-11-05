"""FIX 14: a successful submit clears the streak and keeps the pass going."""

import pytest

from runner.explore_loop import fill
from tests.test_runner_fixes.test_fill_backoff_helpers import install_generator, make_state


def test_success_resets_streak(monkeypatch):
    calls = install_generator(monkeypatch, [{"idx": 0, "budget_low": False}, "CONCURRENT"])
    state = make_state(submit_fail_streak=5)

    fill.fill_slots(None, state, None, max_concurrent=2)

    assert state["submit_fail_streak"] == 0
    assert len(state["inflight"]) == 1
    assert state["batch_idx"] == 2
    assert len(calls) == 2


@pytest.mark.parametrize("fails", [1, 2])
def test_small_streak_keeps_trying(monkeypatch, fails):
    calls = install_generator(monkeypatch, [None] * fails + [{"idx": 0, "budget_low": False}])
    state = make_state()

    fill.fill_slots(None, state, None, max_concurrent=4)

    # failures, the success, then the CONCURRENT probe that ends the pass
    assert len(calls) == fails + 2
    assert state["submit_fail_streak"] == 0
