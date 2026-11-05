"""Live-database fixture shared by the cleanup_db --backup tests."""

import pytest

from core.db import connect
from tools import cleanup_db


@pytest.fixture
def live_db(tmp_path, monkeypatch):
    """A database with committed rows and an open connection."""
    path = tmp_path / "live.duckdb"
    writer = connect(path)
    writer.execute("CREATE TABLE t (x INTEGER)")
    writer.execute("INSERT INTO t VALUES (1), (2), (3)")
    writer.commit()
    monkeypatch.setattr(cleanup_db, "DB_PATH", str(path))
    yield path, writer
    writer.close()
