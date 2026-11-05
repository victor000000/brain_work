"""The SQL statements behind the pyramid_targets snapshot/append model.

Split out of `tools/refresh_pyramid_targets/persist.py`, which re-exports
`HISTORY_TABLE`. `_CREATE_HISTORY` is what makes the history table append-only:
its primary key includes `refreshed_at`, so a later refresh of the same period
inserts alongside the older row instead of replacing it.
"""

HISTORY_TABLE = "pyramid_targets_history"

_COLUMNS = (
    "region",
    "delay",
    "category",
    "alpha_count",
    "multiplier",
    "gap_to_3",
    "score",
    "period_start",
    "period_end",
    "refreshed_at",
)

# Mirrors core/db/schema_sql.py — created when the tool runs against a fresh
# database so the migration is self-sufficient.
_CREATE_CURRENT = """
CREATE TABLE IF NOT EXISTS pyramid_targets (
    region       TEXT    NOT NULL,
    delay        INTEGER NOT NULL,
    category     TEXT    NOT NULL,
    alpha_count  INTEGER NOT NULL DEFAULT 0,
    multiplier   REAL    NOT NULL DEFAULT 1.0,
    gap_to_3     INTEGER NOT NULL DEFAULT 3,
    score        REAL    NOT NULL DEFAULT 0,
    period_start TEXT,
    period_end   TEXT,
    refreshed_at INTEGER NOT NULL,
    PRIMARY KEY (region, delay, category)
)
"""

_CREATE_HISTORY = f"""
CREATE TABLE IF NOT EXISTS {HISTORY_TABLE} (
    region       TEXT    NOT NULL,
    delay        INTEGER NOT NULL,
    category     TEXT    NOT NULL,
    alpha_count  INTEGER NOT NULL DEFAULT 0,
    multiplier   REAL    NOT NULL DEFAULT 1.0,
    gap_to_3     INTEGER NOT NULL DEFAULT 3,
    score        REAL    NOT NULL DEFAULT 0,
    period_start TEXT    NOT NULL DEFAULT '',
    period_end   TEXT    NOT NULL DEFAULT '',
    refreshed_at INTEGER NOT NULL,
    PRIMARY KEY (region, delay, category, period_start, period_end, refreshed_at)
)
"""

_INSERT_HISTORY = f"""
INSERT OR IGNORE INTO {HISTORY_TABLE} ({", ".join(_COLUMNS)})
VALUES ({", ".join(":" + c for c in _COLUMNS)})
"""

_ARCHIVE_CURRENT = f"""
INSERT OR IGNORE INTO {HISTORY_TABLE} ({", ".join(_COLUMNS)})
SELECT region, delay, category, alpha_count, multiplier, gap_to_3, score,
       COALESCE(period_start, ''), COALESCE(period_end, ''), refreshed_at
FROM pyramid_targets
"""

_UPSERT_CURRENT = """
INSERT INTO pyramid_targets
  (region, delay, category, alpha_count, multiplier, gap_to_3, score,
   period_start, period_end, refreshed_at)
VALUES (:region, :delay, :category, :alpha_count, :multiplier, :gap_to_3, :score,
        :period_start, :period_end, :refreshed_at)
ON CONFLICT(region, delay, category) DO UPDATE SET
  alpha_count  = excluded.alpha_count,
  multiplier   = excluded.multiplier,
  gap_to_3     = excluded.gap_to_3,
  score        = excluded.score,
  period_start = excluded.period_start,
  period_end   = excluded.period_end,
  refreshed_at = excluded.refreshed_at
WHERE excluded.refreshed_at >= pyramid_targets.refreshed_at
"""
