"""FIX 13: periodic maintenance drains the held queue every pass, runs the
submission check on its own shorter cadence and fires it on a clock when batch
progress stalls."""

from unittest.mock import MagicMock


def test_maintenance_drains_held_queue_every_pass(monkeypatch, conn):
    from runner.explore_helpers import maintenance

    calls = []
    monkeypatch.setattr(maintenance, "drain_held_queue", lambda session, c: calls.append(1) or 0)
    # done == last_check_done: the heavy CHECK_INTERVAL block must not run,
    # yet the drain still does.
    state = {"done_count": 5, "last_check_done": 5, "inflight": []}

    maintenance.periodic_maintenance(state, conn, MagicMock(), freed=False)

    assert calls


def test_submission_check_runs_on_its_own_shorter_cadence(monkeypatch, conn):
    """The check must not wait for the heavy CHECK_INTERVAL refreshes.

    At ~46 batches per half hour, gating the check on CHECK_INTERVAL (50) left
    a gate-passing alpha unlooked-at for ~30 minutes.
    """
    from runner.explore_helpers import maintenance
    from runner.explore_helpers._constants import CHECK_INTERVAL, CHECK_INTERVAL_SUBMIT

    assert CHECK_INTERVAL_SUBMIT < CHECK_INTERVAL
    checks, heavy = [], []
    monkeypatch.setattr(maintenance, "drain_held_queue", lambda s, c: 0)
    monkeypatch.setattr(maintenance, "start_background_check", lambda: checks.append(1))
    monkeypatch.setattr(maintenance, "load_diversity_weights", lambda c, force=False: heavy.append(1))
    monkeypatch.setattr(maintenance, "_refresh_pyramid_state", lambda s, c: None)
    monkeypatch.setattr(maintenance, "_refresh_cell_priors", lambda c: None)
    monkeypatch.setattr(maintenance, "_refresh_cell_yield_posterior", lambda c: None)
    monkeypatch.setattr(maintenance, "load_cell_yield_posterior", lambda c: None)
    monkeypatch.setattr(maintenance, "_log_progress", lambda s, c: None)

    state = {"done_count": 0, "last_check_done": 0, "last_submit_check_done": 0, "inflight": []}
    for done in (5, 10, 15, 20, 50):
        state["done_count"] = done
        maintenance.periodic_maintenance(state, conn, MagicMock(), freed=False)

    # 10, 20 and 50 cross the submit interval; only 50 crosses the heavy one.
    assert len(checks) == 3, checks
    assert len(heavy) == 1, heavy


def test_checks_fire_on_a_clock_when_progress_stalls(monkeypatch, conn):
    """Budget exhaustion stops batches completing, so a completion-keyed check
    would stop too — for the whole idle window, with eligible alphas waiting."""
    from runner.explore_helpers import maintenance
    from runner.explore_helpers._constants import CHECK_MAX_IDLE_SEC

    checks = []
    monkeypatch.setattr(maintenance, "drain_held_queue", lambda s, c: 0)
    monkeypatch.setattr(maintenance, "start_background_check", lambda: checks.append(1))
    for name in (
        "load_diversity_weights",
        "_refresh_pyramid_state",
        "_refresh_cell_priors",
        "_refresh_cell_yield_posterior",
        "load_cell_yield_posterior",
        "_log_progress",
    ):
        monkeypatch.setattr(maintenance, name, lambda *a, **k: None)

    # done_count frozen (no batches completing), last check long ago
    import time as _t

    state = {
        "done_count": 40,
        "last_check_done": 0,
        "last_submit_check_done": 40,
        "last_submit_check_ts": _t.time() - CHECK_MAX_IDLE_SEC - 1,
        "inflight": [],
    }
    maintenance.periodic_maintenance(state, conn, MagicMock(), freed=False)
    assert len(checks) == 1, "clock should fire the check while progress is stalled"

    # ...and a second pass immediately after does not re-fire.
    maintenance.periodic_maintenance(state, conn, MagicMock(), freed=False)
    assert len(checks) == 1
