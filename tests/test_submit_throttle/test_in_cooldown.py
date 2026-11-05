"""in_cooldown returns True after threshold throttle events in window."""


def test_no_events_not_in_cooldown():
    from runner.submit.flow import _reset_throttle_state, in_cooldown

    _reset_throttle_state()
    assert in_cooldown(("CHN", "TOP2000U", 0), now=0.0) is False


def test_threshold_events_triggers_cooldown():
    from runner.submit.flow import _reset_throttle_state, in_cooldown, record_throttle

    _reset_throttle_state()
    cell = ("HKG", "TOP800", 1)
    for i in range(5):
        record_throttle(cell, now=float(i))
    assert in_cooldown(cell, now=5.0) is True


def test_events_outside_window_drop():
    from runner.submit.flow import _reset_throttle_state, in_cooldown, record_throttle

    _reset_throttle_state()
    cell = ("HKG", "TOP800", 1)
    for i in range(5):
        record_throttle(cell, now=float(i))
    assert in_cooldown(cell, now=65.0) is False


def test_below_threshold_not_in_cooldown():
    from runner.submit.flow import _reset_throttle_state, in_cooldown, record_throttle

    _reset_throttle_state()
    cell = ("USA", "TOP3000", 0)
    for i in range(4):
        record_throttle(cell, now=float(i))
    assert in_cooldown(cell, now=4.0) is False
