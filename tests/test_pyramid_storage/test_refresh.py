"""refresh_if_stale — staleness gate, fetch invocation, fetch-failure path."""

from unittest.mock import MagicMock

from tests.test_pyramid_storage.conftest import mem_conn


def test_refresh_if_stale_skips_when_fresh_and_runs_when_stale(monkeypatch):
    """refresh_if_stale returns False when latest snapshot is recent, True after refresh."""
    from download import pyramid as pyramid_mod

    conn = mem_conn()
    pyramid_mod.store_pyramid_state(
        conn,
        [{"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.6}],
        [{"category": "pv", "region": "USA", "delay": 0, "alpha_count": 0}],
        fetched_at=1000,
    )

    # Pin "now" so we can drive the staleness window deterministically.
    fake_now = 1500
    monkeypatch.setattr(pyramid_mod.time, "time", lambda: fake_now)

    fetch_calls = []

    def fake_fetch(session):
        fetch_calls.append(session)
        return (
            [{"category": "pv", "region": "USA", "delay": 0, "multiplier": 1.7}],
            [{"category": "pv", "region": "USA", "delay": 0, "alpha_count": 1}],
        )

    monkeypatch.setattr(pyramid_mod, "fetch_pyramid_state", fake_fetch)

    # Snapshot is 500s old; max_age=1000 -> still fresh, no refresh.
    assert pyramid_mod.refresh_if_stale(MagicMock(), conn, max_age_seconds=1000) is False
    assert fetch_calls == []

    # Same snapshot now 500s old; max_age=400 -> stale, should refresh.
    assert pyramid_mod.refresh_if_stale(MagicMock(), conn, max_age_seconds=400) is True
    assert len(fetch_calls) == 1

    # New snapshot row at fetched_at = fake_now.
    rows = conn.execute("SELECT fetched_at FROM pyramid_multipliers ORDER BY fetched_at").fetchall()
    assert rows == [(1000,), (1500,)]


def test_refresh_if_stale_returns_false_on_fetch_failure(monkeypatch):
    """If fetch_pyramid_state returns (None, None), no DB write and return False."""
    from download import pyramid as pyramid_mod

    conn = mem_conn()
    monkeypatch.setattr(pyramid_mod.time, "time", lambda: 9999)
    monkeypatch.setattr(pyramid_mod, "fetch_pyramid_state", lambda s: (None, None))

    # No prior snapshot -> always considered stale -> attempts fetch -> fails -> False.
    assert pyramid_mod.refresh_if_stale(MagicMock(), conn, max_age_seconds=1) is False
    assert conn.execute("SELECT COUNT(*) FROM pyramid_multipliers").fetchone()[0] == 0
