"""`connect_for_reading`: a read-only open cannot replay a WAL, so fall back.

Split from the compat tests; see `core/db/compat_conn.py`.
"""

import pytest


def test_connect_for_reading_replays_a_wal_it_cannot_read(tmp_path, monkeypatch):
    """A read-only open fails when DuckDB must replay the WAL first.

    Replaying needs write access to the database file, so `read_only=True` raises
    `Failure while replaying WAL file ... Bad file descriptor`. That is exactly
    the state an inspection tool wants to look at — `make health` was failing
    on it whenever the explorer exited without checkpointing — so the helper
    falls back to a read-write open, which performs the replay.
    """
    from core.db import compat_conn

    calls = []

    def fake_connect(target, **kwargs):
        calls.append((target, kwargs))
        if kwargs.get("read_only"):
            raise compat_conn.OperationalError("IO Error: Failure while replaying WAL file ...: Bad file descriptor")
        return "connection"

    monkeypatch.setattr(compat_conn, "connect", fake_connect)

    assert compat_conn.connect_for_reading(tmp_path / "db.duckdb") == "connection"
    assert len(calls) == 2 and calls[0][1] == {"read_only": True} and not calls[1][1], calls


def test_connect_for_reading_does_not_swallow_a_real_lock_error(tmp_path, monkeypatch):
    """A database held by a running explorer must still fail loudly."""
    from core.db import compat_conn

    monkeypatch.setattr(
        compat_conn, "connect", lambda *a, **k: (_ for _ in ()).throw(compat_conn.OperationalError("Conflicting lock"))
    )
    with pytest.raises(compat_conn.OperationalError):
        compat_conn.connect_for_reading(tmp_path / "db.duckdb")
