"""queue_held_alpha + drain_held_alpha behave as a FIFO with QUEUE_LIMIT cap."""


def test_empty_queue_drains_none():
    from runner.submit.flow import _reset_throttle_state, drain_held_alpha

    _reset_throttle_state()
    assert drain_held_alpha(("X", "Y", 0)) is None


def test_fifo_order():
    from runner.submit.flow import _reset_throttle_state, drain_held_alpha, queue_held_alpha

    _reset_throttle_state()
    cell = ("CHN", "TOP2000U", 0)
    for aid in ("A1", "A2", "A3"):
        queue_held_alpha(cell, aid)
    assert drain_held_alpha(cell) == "A1"
    assert drain_held_alpha(cell) == "A2"
    assert drain_held_alpha(cell) == "A3"
    assert drain_held_alpha(cell) is None


def test_overflow_drops_oldest():
    from runner.submit.flow import (
        QUEUE_LIMIT,
        _reset_throttle_state,
        drain_held_alpha,
        queue_held_alpha,
    )

    _reset_throttle_state()
    cell = ("USA", "TOP3000", 0)
    for i in range(QUEUE_LIMIT + 5):
        queue_held_alpha(cell, f"A{i}")
    assert drain_held_alpha(cell) == "A5"
