"""Selected dispatch identities survive uncertain POSTs and process restarts."""

import duckdb
import pytest

from tools import submit_selected_probe as tool


def test_uncertain_dispatch_reservation_survives_restart(tmp_path, monkeypatch):
    path = str(tmp_path / "attempts.duckdb")
    conn = duckdb.connect(path)
    conn.execute("CREATE TABLE simulations (batch_idx BIGINT)")
    conn.execute("INSERT INTO simulations VALUES (12)")
    conn.execute("CREATE TABLE probe_batches (error_message VARCHAR)")
    conn.execute("INSERT INTO probe_batches VALUES ('B15: acceptance cannot be determined'), (NULL)")
    observed = []

    def uncertain(session, connection, index, *, probe_id):
        observed.append((index, probe_id))
        raise RuntimeError("connection lost after possible POST")

    monkeypatch.setattr(tool, "submit_queued_probe", uncertain)
    with pytest.raises(RuntimeError):
        tool.submit_selected(None, conn, "uncertain-owner")
    conn.close()
    conn = duckdb.connect(path)
    assert tool.reserve_selected_batch(conn, "next-owner") == 17
    assert observed == [(16, "uncertain-owner")]
    assert conn.execute("SELECT * FROM selected_probe_attempts ORDER BY batch_idx").fetchall() == [
        (16, "uncertain-owner"),
        (17, "next-owner"),
    ]
    assert conn.execute("SELECT * FROM simulations").fetchall() == [(12,)]
    conn.close()
