"""When reconcile_submissions flips a status to SUBMITTED, the
submission_outcomes.submitted counter must also bump."""

import pytest

from core.db import connect, init_tables
from runner.submit.outcome import _record_outcome


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_tables(c)
    c.execute(
        "INSERT INTO alpha_results "
        "(alpha_id, template, region, universe, delay, neutralization, status, "
        " is_sharpe, is_fitness, is_turnover, test_sharpe) "
        "VALUES ('A1', 'ts_backfill_negmean', 'CHN', 'TOP2000U', 0, 'NONE', 'UNSUBMITTED', "
        " 2.10, 1.2, 0.05, 0.5)"
    )
    c.commit()
    yield c
    c.close()


def test_record_outcome_bumps_submitted_after_reconcile(conn):
    """Simulate reconcile flipping status, then calling _record_outcome."""
    conn.execute("UPDATE alpha_results SET status='SUBMITTED' WHERE alpha_id='A1'")
    conn.commit()
    _record_outcome(conn, "A1", "SUBMITTED")
    row = conn.execute(
        "SELECT submitted, rejected, throttled FROM submission_outcomes "
        "WHERE template='ts_backfill_negmean' AND region='CHN' AND universe='TOP2000U' AND delay=0 AND neutralization='NONE'"
    ).fetchone()
    assert row == (1, 0, 0)


def test_reconcile_calls_record_outcome(monkeypatch, conn):
    """The reconcile loop, given a session returning dateSubmitted, must bump submitted."""
    from unittest.mock import MagicMock

    class FakeResp:
        status_code = 200

        def json(self):
            return {"dateSubmitted": "2026-05-01T00:00:00Z"}

    fake_session = MagicMock()
    fake_session.get.return_value = FakeResp()

    import tools.reconcile_submissions as rs

    # Wrap conn in a proxy that ignores close() so main() doesn't destroy
    # the shared in-memory connection before we can assert against it.
    class _NoCloseConn:
        def __init__(self, c):
            self._c = c

        def close(self):
            pass  # intentionally suppressed

        def __getattr__(self, name):
            return getattr(self._c, name)

        def __enter__(self):
            return self._c.__enter__()

        def __exit__(self, *args):
            return self._c.__exit__(*args)

    proxy = _NoCloseConn(conn)

    monkeypatch.setattr(rs, "get_session", lambda: fake_session)
    monkeypatch.setattr(rs, "get_conn", lambda: proxy)
    # Disable the time.sleep so the loop runs immediately.
    monkeypatch.setattr(rs.time, "sleep", lambda *a, **k: None)

    rs.main()

    row = conn.execute("SELECT status FROM alpha_results WHERE alpha_id='A1'").fetchone()
    assert row[0] == "SUBMITTED"
    row2 = conn.execute(
        "SELECT submitted FROM submission_outcomes "
        "WHERE template='ts_backfill_negmean' AND region='CHN' AND universe='TOP2000U' AND delay=0"
    ).fetchone()
    assert row2 is not None and row2[0] == 1
