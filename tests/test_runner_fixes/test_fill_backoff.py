"""FIX 14: submit failures back off across passes (transient vs systemic)."""

import time

from runner.explore_loop import fill
from tests.test_runner_fixes.test_fill_backoff_helpers import install_generator, make_state


def test_pass_failure_limit_stops_this_pass_only(monkeypatch):
    calls = install_generator(monkeypatch, [None, None, None, None])
    state = make_state()

    fill.fill_slots(None, state, None, max_concurrent=2)

    assert len(calls) == fill.PASS_FAILURE_LIMIT
    assert state["submit_fail_streak"] == fill.PASS_FAILURE_LIMIT
    assert "submit_backoff_until" not in state  # still under the transient limit


def test_streak_carries_across_passes_and_backs_off(monkeypatch):
    install_generator(monkeypatch, [None, None, None])
    state = make_state()
    fill.fill_slots(None, state, None, max_concurrent=2)
    assert state["submit_fail_streak"] == 3

    install_generator(monkeypatch, [None])
    fill.fill_slots(None, state, None, max_concurrent=2)

    assert state["submit_fail_streak"] == 4
    assert state["submit_backoff_until"] >= time.time() + fill.TRANSIENT_BACKOFF_SEC - 1


def test_systemic_streak_uses_longer_backoff(monkeypatch):
    install_generator(monkeypatch, [None])
    state = make_state(submit_fail_streak=fill.SYSTEMIC_FAIL_LIMIT - 1)

    fill.fill_slots(None, state, None, max_concurrent=2)

    assert state["submit_fail_streak"] == fill.SYSTEMIC_FAIL_LIMIT
    assert state["submit_backoff_until"] >= time.time() + fill.SYSTEMIC_BACKOFF_SEC - 1


def test_active_backoff_skips_submitting(monkeypatch):
    calls = install_generator(monkeypatch, [])
    state = make_state(submit_backoff_until=time.time() + 100)

    fill.fill_slots(None, state, None, max_concurrent=2)

    assert calls == []
