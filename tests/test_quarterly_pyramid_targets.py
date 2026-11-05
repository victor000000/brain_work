"""Genius allocation must use dated quarter counts, through the existing writer."""

import pytest
import requests

from core.db import DBError, connect, init_tables
from download.pyramid import quarter_targets as qt
from generator.diversity_picker.pyramid3 import _eligible_rows
from tools.refresh_pyramid_targets.persist import upsert_on_connection
from tools.refresh_pyramid_targets.score import compute_targets

PERIOD = ("2026-10-01", "2026-12-31")


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_tables(c)
    yield c
    c.close()


def counts(n):
    return [{"category": {"id": "pv"}, "region": "USA", "delay": 1, "alphaCount": n}]


MULTS = [{"category": {"id": "pv"}, "region": "USA", "delay": 1, "multiplier": 1.5}]


def seed(conn, count, period, timestamp):
    upsert_on_connection(conn, compute_targets(counts(count), MULTS, *period, timestamp))


def mock_fetch(monkeypatch, count=0):
    calls = []
    monkeypatch.setattr(qt, "quarter_bounds", lambda: PERIOD)
    monkeypatch.setattr(qt.time, "time", lambda: 2000)

    def fetch(session, start, end):
        calls.append((start, end))
        return counts(count)

    monkeypatch.setattr(qt, "fetch_pyramid_alphas", fetch)
    monkeypatch.setattr(qt, "fetch_pyramid_multipliers", lambda session: MULTS)
    return calls


@pytest.mark.parametrize("old_period", [(None, None), ("2026-07-01", "2026-09-30")])
def test_recent_wrong_period_does_not_suppress_current_refresh(conn, monkeypatch, old_period):
    seed(conn, 2, old_period, 1999)
    calls = mock_fetch(monkeypatch)
    assert qt.refresh_quarter_targets(object(), conn, max_age_seconds=100) is True
    assert calls == [PERIOD]
    assert conn.execute("SELECT alpha_count,gap_to_3,score,period_start FROM pyramid_targets").fetchone() == (
        0,
        3,
        1.5,
        PERIOD[0],
    )
    assert conn.execute("SELECT COUNT(*) FROM pyramid_targets_history").fetchone()[0] == 2
    assert conn.execute("SELECT 42").fetchone() == (42,)  # caller still owns a usable connection


def test_fresh_current_quarter_avoids_network(conn, monkeypatch):
    seed(conn, 0, PERIOD, 1999)
    calls = mock_fetch(monkeypatch)
    assert qt.refresh_quarter_targets(object(), conn, max_age_seconds=100) is False
    assert calls == []


def test_stale_current_quarter_updates_near_completion_gap(conn, monkeypatch):
    seed(conn, 0, PERIOD, 1000)
    mock_fetch(monkeypatch, count=2)
    assert qt.refresh_quarter_targets(object(), conn, max_age_seconds=100) is True
    assert conn.execute("SELECT alpha_count,gap_to_3,score FROM pyramid_targets").fetchone() == (2, 1, 15.0)


def test_missing_data_preserves_counts_instead_of_creating_zero_progress(conn, monkeypatch):
    seed(conn, 2, PERIOD, 1000)
    mock_fetch(monkeypatch)
    monkeypatch.setattr(qt, "fetch_pyramid_alphas", lambda *args: [])
    assert qt.refresh_quarter_targets(object(), conn, max_age_seconds=100) is False
    assert conn.execute("SELECT alpha_count FROM pyramid_targets").fetchone() == (2,)


def test_transport_failure_leaves_existing_snapshot(conn, monkeypatch):
    seed(conn, 2, PERIOD, 1000)
    mock_fetch(monkeypatch)

    def fail(*args):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(qt, "fetch_pyramid_alphas", fail)
    with pytest.raises(requests.ConnectionError):
        qt.refresh_quarter_targets(object(), conn, max_age_seconds=100)
    assert conn.execute("SELECT alpha_count FROM pyramid_targets").fetchone() == (2,)


def test_bad_refresh_rolls_back_history_and_current_rows(conn):
    seed(conn, 2, PERIOD, 1000)
    rows = compute_targets(counts(0), MULTS, *PERIOD, 2000)
    rows[0]["score"] = "invalid-number"
    with pytest.raises(DBError):
        upsert_on_connection(conn, rows)
    assert conn.execute("SELECT alpha_count FROM pyramid_targets").fetchone() == (2,)
    assert conn.execute("SELECT COUNT(*) FROM pyramid_targets_history").fetchone() == (1,)


def test_picker_never_uses_all_time_or_previous_quarter_rows(conn, monkeypatch):
    from generator.diversity_picker import pyramid3_targets as target_module

    monkeypatch.setattr(target_module, "quarter_bounds", lambda: PERIOD)
    seed(conn, 2, (None, None), 1000)
    assert _eligible_rows(conn, [("USA", "TOP3000", 1)]) == []
    seed(conn, 2, ("2026-07-01", "2026-09-30"), 1001)
    assert _eligible_rows(conn, [("USA", "TOP3000", 1)]) == []
    seed(conn, 0, PERIOD, 1002)
    monkeypatch.setattr(target_module, "_available_categories", lambda *args: None)
    assert _eligible_rows(conn, [("USA", "TOP3000", 1)])[0][0] == ("USA", 1, "pv", 1.5)


def test_startup_refreshes_quarter_targets_through_existing_connection(conn, monkeypatch):
    from runner.explore_loop import startup

    calls = []
    session = object()
    monkeypatch.setattr(startup, "refresh_quarter_targets", lambda s, c: calls.append((s, c)))
    monkeypatch.setattr(startup, "start_background_check", lambda: None)
    startup._startup_checks(session, conn)
    assert calls == [(session, conn)]


def test_maintenance_attempts_quarter_targets_when_lifetime_refresh_fails(monkeypatch):
    from runner.explore_helpers import maintenance_refresh as maintenance

    calls = []
    session = object()

    def fail(*args, **kwargs):
        raise RuntimeError("old snapshot refresh failed")

    monkeypatch.setattr(maintenance, "refresh_if_stale", fail)
    monkeypatch.setattr(maintenance, "refresh_quarter_targets", lambda s, c, **kw: calls.append((s, c)))
    maintenance._refresh_pyramid_state(session, conn)
    assert calls == [(session, conn)]
