"""Simulation-error incident breaker: a streak of resultless batches pauses submits."""

import time

from runner.explore_loop import error_breaker as eb


def _fail(state, n):
    for _ in range(n):
        eb.note_batch_done(state, failed=True)


def test_pause_is_armed_exactly_at_the_streak_limit():
    state = {}
    _fail(state, eb.STREAK_LIMIT - 1)
    assert eb.paused(state) is False
    assert state["sim_error_streak"] == eb.STREAK_LIMIT - 1

    _fail(state, 1)
    assert state["sim_error_pause_until"] > time.time()
    assert eb.paused(state) is True
    # Arming consumes the streak; the next window counts fresh failures.
    assert state["sim_error_streak"] == 0


def test_a_success_resets_streak_and_backoff():
    state = {"sim_error_streak": 3, "error_backoff_count": 2}
    eb.note_batch_done(state, failed=False)
    assert state["sim_error_streak"] == 0
    assert state["error_backoff_count"] == 0


def test_a_success_disarms_an_armed_pause():
    """A batch completing with results ends the window, backoff included."""
    state = {}
    _fail(state, eb.STREAK_LIMIT)
    assert eb.paused(state) is True
    eb.note_batch_done(state, failed=False)
    assert eb.paused(state) is False
    assert state["sim_error_pause_until"] == 0.0


def test_backoff_doubles_after_the_pause_expires():
    state = {}
    _fail(state, eb.STREAK_LIMIT)
    first = state["sim_error_pause_until"] - time.time()
    assert 0 < first <= eb.PAUSE_SEC + 1

    # The window persists across the pause: a fresh streak pauses longer.
    state["sim_error_pause_until"] = time.time() - 1
    _fail(state, eb.STREAK_LIMIT)
    second = state["sim_error_pause_until"] - time.time()
    assert eb.PAUSE_SEC < second <= 2 * eb.PAUSE_SEC + 1


def test_backoff_is_capped():
    state = {"error_backoff_count": 10}
    _fail(state, eb.STREAK_LIMIT)
    assert state["sim_error_pause_until"] - time.time() <= eb.PAUSE_MAX + 1


def test_expired_pause_clears_without_a_new_streak():
    state = {"sim_error_pause_until": time.time() - 5}
    assert eb.paused(state) is False
    assert state["sim_error_pause_until"] == 0.0


# ── the feed ─────────────────────────────────────────────────────────────
# `note_batch_done` is only as good as what calls it. For 10-06..10-09 the
# answer was "nothing that fires": the one writer of `failed` was the terminal
# no-result write-off, which returns None whenever the parent body lists
# children, and the platform's real failure shape is a parent whose children
# all come back FAIL. 2,859 such parents exist. These tests pin the second
# feed — a complete batch with no successful child — which is the same signal
# `poll_children_fetch` can produce in exactly one way: the platform answering
# HTTP 200 with a status outside COMPLETE/WARNING.


def _poll_multi_with(monkeypatch, counts):
    """Run `_poll_multi` with `handle_children` returning `counts`."""
    from runner import poll_batch, poll_batch_results

    monkeypatch.setattr(poll_batch, "handle_children", lambda *a, **k: counts)
    monkeypatch.setattr(poll_batch_results, "update_sim_status", lambda *a, **k: None)
    info = {"idx": 1, "pid": "p1"}
    settings = {"region": "USA", "universe": "TOP3000"}
    done = poll_batch_results._poll_multi(None, info, ["c"] * 10, None, settings, 0.0, 30.0)
    return done, info


def test_a_batch_whose_every_child_failed_is_marked_failed(monkeypatch):
    done, info = _poll_multi_with(monkeypatch, (0, 10, True))
    assert done is True
    assert info["failed"] is True


def test_a_partly_successful_batch_is_not_marked_failed(monkeypatch):
    """Results mean the platform is working; the streak should reset."""
    done, info = _poll_multi_with(monkeypatch, (8, 2, True))
    assert done is True
    assert "failed" not in info


def test_a_repoll_that_stores_nothing_is_not_marked_failed(monkeypatch):
    """The healthy-path shape the old comment cited: err=0, so no failure."""
    done, info = _poll_multi_with(monkeypatch, (0, 0, True))
    assert done is True
    assert "failed" not in info


def test_an_all_fail_streak_reaches_the_pause(monkeypatch):
    """End to end: four all-FAIL batches arm the breaker through the real feed."""
    state = {}
    for _ in range(eb.STREAK_LIMIT):
        _, info = _poll_multi_with(monkeypatch, (0, 10, True))
        eb.note_batch_done(state, bool(info.get("failed")))
    assert eb.paused(state) is True
