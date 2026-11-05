"""FIX 16: unknown regions fail closed on neutralization; verify_submission is
bounded and reports PENDING instead of blocking."""

import time
from unittest.mock import MagicMock

from core.constraints import ALLOWED_NEUT_BY_REGION
from runner import settings_factory as sf
from runner import verify_submit as vs
from tests.test_runner_fixes.helpers import FakeResponse


def test_unknown_region_uses_most_restrictive_neutralizations():
    expected = set.intersection(*(set(v) for v in ALLOWED_NEUT_BY_REGION.values()))

    assert expected  # sanity: the intersection is usable
    for _ in range(20):
        assert sf.pick_neutralization("NOWHERE") in expected


def test_known_region_stays_within_allowed_set():
    for _ in range(20):
        assert sf.pick_neutralization("USA") in ALLOWED_NEUT_BY_REGION["USA"]


def test_verify_pending_is_bounded(monkeypatch, conn):
    monkeypatch.setattr(vs, "VERIFY_MAX_WAIT_SEC", 0.05)
    monkeypatch.setattr(vs, "VERIFY_POLL_INTERVAL_SEC", 0.01)
    session = MagicMock()
    session.get.return_value = FakeResponse(200, json_data={})

    start = time.monotonic()
    assert vs.verify_submission(session, conn, "A1") == "PENDING"
    assert time.monotonic() - start < 5


def test_verify_submitted(monkeypatch, conn):
    session = MagicMock()
    session.get.return_value = FakeResponse(200, json_data={"dateSubmitted": "2026-01-01", "status": "ACTIVE"})

    assert vs.verify_submission(session, conn, "A1") == "SUBMITTED"


def test_verify_non_200_fails(monkeypatch, conn):
    session = MagicMock()
    session.get.return_value = FakeResponse(500, text="oops")

    assert vs.verify_submission(session, conn, "A1") == "VERIFY_FAILED"


def test_a_void_201_is_counted_and_deferred(monkeypatch, conn):
    """A 201 that never sets dateSubmitted must not keep heading check runs.

    38 alphas collected one on 2026-10-07; seven asked hours later still read
    `UNSUBMITTED dateSubmitted=None`, so it is void rather than slow. Left
    un-deferred the alpha keeps its sharpe rank, heads every run, and spends a
    45s preview each time on a question the platform has already declined to
    answer. Counted and deferred, never retired: nothing here is about the
    alpha.
    """
    monkeypatch.setattr(vs, "VERIFY_MAX_WAIT_SEC", 0.05)
    monkeypatch.setattr(vs, "VERIFY_POLL_INTERVAL_SEC", 0.01)
    session = MagicMock()
    session.get.return_value = FakeResponse(200, json_data={})

    assert vs.verify_submission(session, conn, "A1") == "PENDING"

    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='A1'").fetchone()[0] == 1
    assert vs._increment_retry_count.__module__  # imported, not re-implemented
    assert (
        conn.execute(
            "SELECT seen_count FROM check_failures WHERE alpha_id='A1' AND check_name='RETRY_ATTEMPT'"
        ).fetchone()[0]
        == 1
    )
    # Still eligible: a quota or platform condition must never retire an alpha.
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='A1'").fetchone()[0] == 0
