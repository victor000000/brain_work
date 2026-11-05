"""FIX 5: a congested check run stops at its wall-clock budget instead of
holding the checker's thread for hours."""

from checker import auto_check
from tests.test_runner_fixes.auto_check_helpers import _gates_pass, _seed  # noqa: F401


def test_a_congested_run_stops_at_its_wall_clock_budget(monkeypatch, conn):
    """A run must not hold the checker's thread for hours.

    `start_background_check` no-ops while a run is in flight, so a 60-alpha run
    against a congested platform — 45s preview + two 60s correlation polls each
    — locks out every other alpha for the duration. Seen 2026-10-06: a run
    started 08:27 with 43 alphas and was still going 45 minutes later.
    """
    for i in range(6):
        _seed(conn, f"A{i}", 3.0 - i * 0.1)
    seen = []

    def slow_preview(session, aid):
        seen.append(aid)
        return [{"name": "LOW_SHARPE", "result": "PASS"}]

    # One alpha costs 700s of the 1200s budget, so the second must be skipped.
    clock = {"t": 0.0}

    def tick():
        clock["t"] += 700.0
        return clock["t"]

    monkeypatch.setattr(auto_check, "check_via_get", slow_preview)
    monkeypatch.setattr(auto_check.time, "monotonic", tick)
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)
    # The alpha that fits inside the budget must not reach the real submit
    # path: this test passes session=None.
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda s, c, aid: submitted.append(aid) or "FAIL:1")

    auto_check.check_new_alphas(None, conn, limit=20)

    assert len(seen) == 1, f"run did not stop early: {seen}"
    assert submitted == ["A0"], submitted
