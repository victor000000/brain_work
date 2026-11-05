"""FIX 14: a low budget pauses new submits without dropping the accepted batch,
and a CONCURRENT probe ends the pass without a failure."""

from runner.explore_loop import fill
from tests.test_runner_fixes.test_fill_backoff_helpers import install_generator, make_state


def test_low_budget_keeps_batch_and_pauses(monkeypatch):
    batch = {"idx": 0, "budget_low": True, "budget_remaining": 10}
    calls = install_generator(monkeypatch, [batch])
    state = make_state()

    fill.fill_slots(None, state, None, max_concurrent=4)

    assert state["inflight"] == [batch]  # accepted batch stays in flight
    assert state["budget_exhausted"] is True
    assert len(calls) == 1  # paused, no further submits


def test_budget_result_pauses(monkeypatch):
    calls = install_generator(monkeypatch, ["BUDGET"])
    state = make_state()

    fill.fill_slots(None, state, None, max_concurrent=4)

    assert state["budget_exhausted"] is True
    assert len(calls) == 1


def test_concurrent_still_probes_next_pass(monkeypatch):
    calls = install_generator(monkeypatch, ["CONCURRENT"])
    state = make_state()

    fill.fill_slots(None, state, None, max_concurrent=4)

    assert state["concurrent"] is True
    assert len(calls) == 1
    assert state["inflight"] == []
