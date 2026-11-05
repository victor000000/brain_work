"""The health check must survive a database it cannot open.

Split out of `tests/test_healthcheck_main.py`.
"""


def test_main_survives_a_held_write_lock(tmp_path, monkeypatch, capsys):
    """A running explorer holds DuckDB's only write lock — that is not a crash.

    This check has a "processes: explorer running" step, so it is meant to be
    run during operation; before this it died with an unhandled traceback in
    exactly that case. The checks that need no database still run and report.
    """
    from tools.healthcheck import __main__ as hc

    monkeypatch.setattr(hc, "DB_PATH", str(tmp_path / "brain_data.duckdb"))
    (tmp_path / "brain_data.duckdb").write_bytes(b"")

    def locked(*a, **k):
        raise hc.OperationalError("IO Error: Could not set lock on file: Conflicting lock is held")

    monkeypatch.setattr(hc, "connect_for_reading", locked)
    monkeypatch.setattr(hc, "check_templates", lambda: True)
    monkeypatch.setattr(hc, "check_processes", lambda: True)
    logs = tmp_path / "logs"
    logs.mkdir()
    for i in range(11):
        (logs / f"{i}.log").write_text("")
    monkeypatch.setattr(hc, "LOG_DIR", str(logs))

    rc = hc.main()

    out = capsys.readouterr().out
    assert "SKIP" in out and "write lock" in out
    assert rc == 0, "a lock conflict is a skip, not a failure"
