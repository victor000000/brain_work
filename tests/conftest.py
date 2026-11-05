"""Test isolation — keep test runs off the live logs, budget file and DB.

pytest imports this before any test module, so patching LOG_DIR here covers
the file loggers that project modules create when they are imported during
collection. Without it every run appended test fixtures to the real
~/brain_logs (which `make status` reads) and could write the shared
budget-state file.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import duckdb
import pytest

from core.db import OperationalError

_TMP_DIR = tempfile.mkdtemp(prefix="brain_test_")
atexit.register(shutil.rmtree, _TMP_DIR, ignore_errors=True)

# Budget exhaustion state is shared across processes via this file; tests must
# never read or write the production one.
os.environ.setdefault("BRAIN_BUDGET_STATE_PATH", os.path.join(_TMP_DIR, "budget_state.json"))

# The template-attribution ledger is the same kind of shared state, appended to
# on every generated expression; tests must never touch the production one.
os.environ.setdefault("BRAIN_EXPR_TEMPLATE_PATH", os.path.join(_TMP_DIR, "expr_templates.tsv"))

# The portable test target is offline even on a checkout containing real data.
# Guard the raw driver too: wrapper-only protection misses direct DuckDB calls.
if os.environ.get("BRAIN_TEST_OFFLINE") == "1":
    _raw_duckdb_connect = duckdb.connect
    _project_database = Path(__file__).resolve().parents[1] / "brain_data.duckdb"

    def _offline_duckdb_connect(database=":memory:", *args, **kwargs):
        if database is not None and str(database) != ":memory:" and Path(str(database)).resolve() == _project_database:
            raise RuntimeError("Offline tests cannot open the project database")
        return _raw_duckdb_connect(database, *args, **kwargs)

    duckdb.connect = _offline_duckdb_connect


@pytest.fixture(autouse=True)
def _isolate_template_ledger(tmp_path, monkeypatch):
    """One ledger per test.

    The ledger is durable by design — a fresh process folds it back into the
    in-memory map — so without this a test that asserts on `expr_templates`
    sees the entries every earlier test recorded. The collection-time
    `setdefault` above keeps the suite off the production file; this keeps
    tests off each other.
    """
    monkeypatch.setenv("BRAIN_EXPR_TEMPLATE_PATH", str(tmp_path / "expr_templates.tsv"))


# Redirect file logging. core.log_config builds LOG_DIR at import; core.log
# binds it with `from ... import LOG_DIR`, so patch both (whichever imported
# first, the other is covered).
import core.log_config as _log_config  # noqa: E402

_log_config.LOG_DIR = _TMP_DIR
try:
    import core.log as _log

    _log.LOG_DIR = _TMP_DIR
except Exception:  # pragma: no cover - core.log is expected to import
    pass

# Patching LOG_DIR above is not enough on its own: the tool packages build
# module-level `logging.FileHandler`s against `core.log_config.LOG_DIR` when
# they are imported during collection. The patch lands before any of those
# imports (conftest is imported first), so a `from core.log_config import
# LOG_DIR` in a tool module picks up the sandbox value. The guard test in
# tests/test_log_isolation.py pins that no handler ends up in the real
# brain_logs/.


def open_prod_db():
    """Open the production database, skipping when it cannot be read.

    Two legitimate reasons it cannot: a clean checkout has no data, and while
    the explorer is running it holds DuckDB's single-process lock. Both mean
    "this integration test cannot run right now", not "the code is broken".
    """
    if os.environ.get("BRAIN_TEST_OFFLINE") == "1":
        pytest.skip("live corpus integration test excluded from offline validation")

    from core.db import DB_PATH, get_conn

    if not os.path.exists(DB_PATH):
        pytest.skip("production database not present — integration test")
    try:
        return get_conn()
    except OperationalError:
        pytest.skip("production database is held by a running explorer — integration test")


@pytest.fixture(autouse=True)
def _fresh_generation_memory():
    """Clear the generator's cross-batch duplicate memory.

    `_recent`/`_recent_set` persist across `collect_valid` calls by design, so
    an expression one test generated is suppressed as a duplicate in the next —
    `test_generator_order`'s five-string pool was partly spent by an earlier
    test, so it passed alone and failed in the full suite.
    """
    from generator import random_generator_rounds as rounds

    rounds._recent.clear()
    rounds._recent_set.clear()
    yield
    rounds._recent.clear()
    rounds._recent_set.clear()


@pytest.fixture
def prod_conn():
    """Connection to the production DB, skipping when it is absent or empty.

    Tests using this are integration checks against the real field/results
    corpus (100K+ fields); a clean checkout cannot run them, so they skip
    instead of failing.
    """
    conn = open_prod_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM data_fields").fetchone()[0]
    except OperationalError:
        count = 0
    if not count:
        conn.close()
        pytest.skip("production database has no field data — integration test")
    yield conn
    conn.close()
