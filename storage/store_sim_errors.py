"""The `sim_errors` sidecar: its schema, and the per-sim error upsert.

Split out of `storage/store_sim.py`, which re-exports both names so
`from storage.store_sim import _record_error` keeps resolving.
"""

import json


def _ensure_sim_errors_schema(conn):
    """Create sim_errors, adding the sim_id column + unique index on legacy DBs.

    DuckDB has no AUTOINCREMENT, so the id is drawn from an explicit sequence
    (its pre-DuckDB equivalent, and the values migrate across unchanged).
    """
    conn.execute("CREATE SEQUENCE IF NOT EXISTS sim_errors_id_seq")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_errors (
            id BIGINT PRIMARY KEY DEFAULT nextval('sim_errors_id_seq'),
            expression TEXT, region TEXT,
            error_message TEXT, settings TEXT, ts TEXT,
            sim_id TEXT
        )
    """)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(sim_errors)")}
    if "sim_id" not in cols:
        conn.execute("ALTER TABLE sim_errors ADD COLUMN sim_id TEXT")
    # NULL sim_id values (legacy rows) are distinct in SQLite, so this is safe
    # to create even with pre-existing rows.
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sim_errors_sim_id ON sim_errors(sim_id)")


def _record_error(conn, expr, region, error_msg, settings, ts, sim_id=None):
    """Save failed simulation to sim_errors.

    Idempotent per sim: when sim_id is known, a re-poll of the same failing sim
    updates the existing row instead of appending a duplicate.
    """
    _ensure_sim_errors_schema(conn)
    payload = (expr, region, error_msg, json.dumps(settings), ts, sim_id)
    if sim_id:
        conn.execute(
            """
            INSERT INTO sim_errors (expression,region,error_message,settings,ts,sim_id)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(sim_id) DO UPDATE SET
                expression=excluded.expression,
                region=excluded.region,
                error_message=excluded.error_message,
                settings=excluded.settings,
                ts=excluded.ts
        """,
            payload,
        )
    else:
        conn.execute(
            "INSERT INTO sim_errors (expression,region,error_message,settings,ts,sim_id) VALUES (?,?,?,?,?,?)",
            payload,
        )
