"""Idempotent column-add migrations applied on every init_tables() call.

CREATE TABLE IF NOT EXISTS does not cover ALTER, so each helper inspects
the current PRAGMA table_info before adding its column. Every entry point
calls init_tables(), so two processes (or threads) can race the check-then-
ALTER — the loser gets "duplicate column name", which is benign and must not
crash startup.
"""

import threading

from core.db.compat import OperationalError

# Serializes check+ALTER within this process; the duplicate-column catch
# covers the cross-process race.
_MIGRATION_LOCK = threading.Lock()


def _add_column(conn, table, column, ddl):
    """Idempotently add `column` to `table`, tolerating a lost race."""
    with _MIGRATION_LOCK:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column in cols:
            return
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        except OperationalError as err:
            # Another connection added it between our PRAGMA and ALTER.
            if "duplicate column name" not in str(err).lower():
                raise


def ensure_template_column(conn):
    """Adds `template TEXT` to alpha_results when missing."""
    _add_column(conn, "alpha_results", "template", "template TEXT")


def ensure_pyramid_categories_column(conn):
    """Adds `pyramid_categories TEXT` to alpha_results when missing.

    Stores a sorted JSON array of distinct pyramid category IDs derived from
    the alpha's expression (via storage.track_pyramid.derive_pyramid_categories).
    """
    _add_column(conn, "alpha_results", "pyramid_categories", "pyramid_categories TEXT")


def ensure_expected_multiplier_column(conn):
    """Adds `expected_multiplier REAL NOT NULL DEFAULT 1.0` to cell_priors.

    Default 1.0 means "no pyramid bias" — pre-refresh state. After the first
    refresh_priors run against populated pyramid data, the value is overwritten
    with the computed expected multiplier for the cell.
    """
    _add_column(conn, "cell_priors", "expected_multiplier", "expected_multiplier REAL NOT NULL DEFAULT 1.0")


def ensure_polish_tried_column(conn):
    """Adds `tried TEXT NOT NULL DEFAULT ''` to polish_candidates when missing.

    Records the neutralizations a candidate has already been polished under, so
    `variant_neutralization` can exclude them. Without it a candidate can be
    re-run under a neutralization it has already been simulated with, which is
    an identical simulation: same expression, same cell, same settings.
    """
    _add_column(conn, "polish_candidates", "tried", "tried TEXT NOT NULL DEFAULT ''")
