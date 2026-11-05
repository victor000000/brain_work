"""FIX 15: restart accounting resets after healthy runs, SystemExit from the
loop is caught, and hitting the restart cap exits non-zero."""

from unittest.mock import Mock

import simulate_alphas as sa


class FakeTime:
    """Stand-in for the `time` module inside simulate_alphas (no global patch)."""

    def __init__(self, values=None):
        self._values = list(values or [])
        self._last = 0.0
        self.slept = []

    def time(self):
        if self._values:
            self._last = self._values.pop(0)
        return self._last

    def sleep(self, seconds):
        self.slept.append(seconds)


def _install_main(monkeypatch, loop, clock_values=()):
    monkeypatch.setattr(sa, "get_conn", lambda: Mock())
    monkeypatch.setattr(sa, "init_tables", lambda conn: None)
    monkeypatch.setattr(sa, "_session_or_none", lambda: object())
    monkeypatch.setattr(sa, "run_explore_loop", loop)
    monkeypatch.setattr(sa, "MAX_RESTARTS", 2)
    monkeypatch.setattr(sa, "RESTART_DELAY", 0)
    fake_time = FakeTime(clock_values)
    monkeypatch.setattr(sa, "time", fake_time)
    return fake_time


def test_max_restarts_exits_nonzero(monkeypatch):
    crashes = []

    def loop(session, conn, max_concurrent):
        crashes.append(1)
        raise SystemExit("accepted batch died")

    _install_main(monkeypatch, loop, clock_values=[1000.0, 2000.0, 2000.0, 2000.0])

    assert sa.main() == 1
    assert len(crashes) == 2  # MAX_RESTARTS


def test_healthy_run_resets_restart_counter(monkeypatch):
    crashes = []

    def loop(session, conn, max_concurrent):
        crashes.append(1)
        raise RuntimeError("boom")

    # First run looks healthy (>= HEALTHY_RUN_SEC), the second does not, so the
    # counter resets to 1 and then reaches 2 instead of dying at the first pair.
    _install_main(monkeypatch, loop, clock_values=[1000.0, 2000.0, 2000.0, 2000.0])

    assert sa.main() == 1
    assert len(crashes) == 2


def test_keyboard_interrupt_exits_zero(monkeypatch):
    def loop(session, conn, max_concurrent):
        raise KeyboardInterrupt

    _install_main(monkeypatch, loop)

    assert sa.main() == 0
