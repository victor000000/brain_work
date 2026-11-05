"""Explorer startup must preserve indexes restored by WAL replay (#26106)."""

import subprocess
import sys

import duckdb


def test_startup_checkpoint_precedes_schema_and_auth(monkeypatch):
    import simulate_alphas as app

    events = []

    class Connection:
        def execute(self, sql):
            events.append(sql)

    monkeypatch.setattr(app, "get_conn", Connection)
    monkeypatch.setattr(app, "init_tables", lambda conn: events.append("schema"))
    monkeypatch.setattr(app, "_session_or_none", lambda: events.append("auth"))
    assert app.main() == 1
    assert events == ["CHECKPOINT", "schema", "auth"]


def test_startup_preserves_replayed_index_through_automatic_checkpoint(tmp_path):
    path = str(tmp_path / "replay.duckdb")
    create = f"""
import os, duckdb
c = duckdb.connect({path!r})
c.execute('CREATE TABLE t(id INTEGER, k VARCHAR)')
c.execute('CREATE INDEX ix ON t(k)')
c.execute('CHECKPOINT')
c.execute("INSERT INTO t SELECT i, 'k'||i FROM range(500) r(i)")
os._exit(0)
"""
    subprocess.run([sys.executable, "-c", create], check=True)
    # Run the real startup checkpoint; replace only later schema/auth work.
    startup = f"""
import os, duckdb
import simulate_alphas as app
app.get_conn = lambda: duckdb.connect({path!r})
def schema(c):
    c.execute("SET wal_autocheckpoint='1KB'")
    c.execute('CREATE TABLE filler AS SELECT * FROM range(20000)')
    os._exit(0)
app.init_tables = schema
app.main()
"""
    subprocess.run([sys.executable, "-c", startup], check=True)
    conn = duckdb.connect(path)
    try:
        assert conn.execute("SELECT count(*) FROM t WHERE k='k7'").fetchone() == (1,)
        conn.execute("DELETE FROM t")
        assert conn.execute("SELECT count(*) FROM t").fetchone() == (0,)
    finally:
        conn.close()
