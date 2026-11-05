"""Alpha activity, results tracking and database-scale healthcheck thresholds."""

from tests import test_healthcheck_helpers as hc
from tests.test_healthcheck_helpers import _seed_healthy
from tools.healthcheck import checks

conn = hc.conn  # the shared fixture, registered here for the tests below


# ── alpha activity ────────────────────────────────────────────────


def test_alpha_recency_recent_passes(conn):
    _seed_healthy(conn)
    assert checks.check_alpha_recency(conn) is True


def test_alpha_recency_stale_fails(conn):
    """The live DB's newest alpha is from 2026-06-01 — this must catch it."""
    _seed_healthy(conn)
    conn.execute("UPDATE alpha_results SET created_at='2026-06-01T14:29:47-04:00'")
    assert checks.check_alpha_recency(conn) is False


def test_explorer_progress_fails_when_stalled(conn):
    _seed_healthy(conn)
    conn.execute("UPDATE alpha_results SET created_at='2026-06-01T14:29:47-04:00'")
    assert checks.check_explorer_progress(conn) is False


def test_explorer_progress_passes_when_fresh(conn):
    _seed_healthy(conn)
    assert checks.check_explorer_progress(conn) is True


# ── results / database thresholds ─────────────────────────────────


def test_results_template_tracking_uses_templated_denominator(conn):
    _seed_healthy(conn, alphas=10, tracked=5)
    assert checks.check_results(conn) is False
    conn.execute("UPDATE template_performance SET template=NULL")  # no-op, keep rows
    conn.executemany("INSERT INTO template_performance VALUES ('tpl', 'USA')", [()] * 5)
    assert checks.check_results(conn) is True


def test_database_thresholds_are_scope_scale(conn, monkeypatch):
    """In-scope DB holds ~196k fields / 47 datasets — 100k/20 must pass."""
    _seed_healthy(conn)
    monkeypatch.setattr(checks, "MIN_FIELDS", 1)
    monkeypatch.setattr(checks, "MIN_DATASETS", 1)
    monkeypatch.setattr(checks, "MIN_REGIONS", 1)
    assert checks.check_database(conn) is True


def test_integrity_check_passes_on_healthy_db(conn):
    assert checks.check_integrity(conn) is True
