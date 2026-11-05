"""Migration helpers must tolerate concurrent entry points racing init_tables.

Two processes can both see a missing column and both issue the ALTER; the
loser gets "duplicate column name", which is benign and must not crash
startup. Any other OperationalError must still propagate.
"""

import threading

import pytest

from core.db import OperationalError, connect, migrations


class _RacingConn:
    """PRAGMA pretends the column is missing; ALTER loses the race."""

    def __init__(self, error):
        self.error = error

    def execute(self, sql):
        if sql.startswith("PRAGMA"):
            return []
        raise self.error


def test_duplicate_column_error_is_tolerated():
    conn = _RacingConn(OperationalError("duplicate column name: template"))
    migrations.ensure_template_column(conn)
    migrations.ensure_pyramid_categories_column(conn)


def test_other_operational_errors_still_raise():
    conn = _RacingConn(OperationalError("database is locked"))
    with pytest.raises(OperationalError):
        migrations.ensure_template_column(conn)


def test_existing_column_is_not_altered():
    class _Existing:
        def __init__(self):
            self.statements = []

        def execute(self, sql):
            self.statements.append(sql)
            if sql.startswith("PRAGMA"):
                return [(0, "template", "TEXT", 0, None, 0)]
            raise AssertionError("must not ALTER an existing column")

    conn = _Existing()
    migrations.ensure_template_column(conn)
    assert all(s.startswith("PRAGMA") for s in conn.statements)


def test_concurrent_migration_threads(tmp_path):
    """Many threads calling the helpers on a shared file DB must not crash."""
    db_path = tmp_path / "race.db"
    conn = connect(db_path)
    conn.execute("CREATE TABLE alpha_results (id INTEGER)")
    conn.execute("CREATE TABLE cell_priors (id INTEGER)")
    conn.commit()
    conn.close()

    barrier = threading.Barrier(8)
    errors = []

    def worker():
        c = connect(db_path)
        try:
            barrier.wait(timeout=10)
            for _ in range(5):
                migrations.ensure_template_column(c)
                migrations.ensure_pyramid_categories_column(c)
                migrations.ensure_expected_multiplier_column(c)
                c.commit()
        except Exception as err:  # pragma: no cover - failure path
            errors.append(err)
        finally:
            c.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert errors == []
    checker = connect(db_path)
    alpha_cols = {row[1] for row in checker.execute("PRAGMA table_info(alpha_results)")}
    prior_cols = {row[1] for row in checker.execute("PRAGMA table_info(cell_priors)")}
    checker.close()
    assert {"template", "pyramid_categories"} <= alpha_cols
    assert "expected_multiplier" in prior_cols
