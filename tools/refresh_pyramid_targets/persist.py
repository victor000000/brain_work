"""Snapshot-safe persistence for pyramid_targets.

The old upsert keyed on (region, delay, category) and replaced the only stored
snapshot in place: a refresh for Q3 2026 overwrote the Q2 2026 rows, with no way
back. Targets are now appended to `pyramid_targets_history` — one row per
(region, delay, category, period, refreshed_at) — which is never updated or
deleted, so an existing period's rows survive every later refresh. The
`pyramid_targets` table keeps one row per cell (the newest snapshot), which is
the contract the picker reads.

`ensure_schema` is the migration: it creates the history table and archives
whatever the current table holds, so the pre-existing snapshot is preserved
even on the first run after this change.

Writing requires an explicit flag (`--apply`); see runner.py.
"""

from core.db import connect
from tools.refresh_pyramid_targets._config import DB_PATH
from tools.refresh_pyramid_targets._log import log
from tools.refresh_pyramid_targets._schema_sql import (
    _ARCHIVE_CURRENT,
    _CREATE_CURRENT,
    _CREATE_HISTORY,
    _INSERT_HISTORY,
    _UPSERT_CURRENT,
    HISTORY_TABLE,
)


def _history_rows(rows):
    """Bind a row for the history table, mapping NULL periods to ''."""
    out = []
    for r in rows:
        item = dict(r)
        item["period_start"] = item.get("period_start") or ""
        item["period_end"] = item.get("period_end") or ""
        out.append(item)
    return out


def ensure_schema(conn, *, commit=True):
    """Migration: create the history table and archive the current snapshot.

    Returns the number of rows newly archived. Idempotent — the archive is
    keyed by refreshed_at, so re-running does not duplicate.
    """
    conn.execute(_CREATE_CURRENT)
    conn.execute(_CREATE_HISTORY)
    archived = 0
    if conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema='main' AND table_name='pyramid_targets'"
    ).fetchone():
        # DuckDB's rowcount is -1 for INSERT, so count the RETURNING rows
        # (INSERT OR IGNORE yields only the rows actually archived).
        archived = len(conn.execute(f"{_ARCHIVE_CURRENT} RETURNING 1").fetchall())
    if commit:
        conn.commit()
    if archived:
        log.info("Archived %d existing pyramid_targets rows into %s", archived, HISTORY_TABLE)
    return archived


def upsert_on_connection(conn, rows):
    """Refresh targets atomically using the explorer's existing writer connection."""
    if not rows:
        return {"archived": 0, "history": 0, "current": 0}
    with conn:
        archived = ensure_schema(conn, commit=False)
        history_rows = _history_rows(rows)
        conn.executemany(_INSERT_HISTORY, history_rows)
        conn.executemany(_UPSERT_CURRENT, rows)
    log.info("Target snapshot written: %d rows (%d archived)", len(rows), archived)
    return {"archived": archived, "history": len(rows), "current": len(rows)}


def upsert(rows, db_path: str | None = None):
    """Append history and update targets, closing only the connection we open."""
    if not rows:
        return {"archived": 0, "history": 0, "current": 0}
    conn = connect(db_path or DB_PATH)
    try:
        return upsert_on_connection(conn, rows)
    finally:
        conn.close()
