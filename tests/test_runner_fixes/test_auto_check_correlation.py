"""An undecided correlation arm reaches the submit rather than parking the alpha."""

from checker import auto_check
from tests.test_runner_fixes.auto_check_helpers import _gates_pass, _seed  # noqa: F401


def test_unavailable_correlation_submits_instead_of_deferring(monkeypatch, conn):
    """An unreadable arm must reach the submit, not park the alpha.

    The platform recomputes correlation at submit time — measured 2026-10-07,
    `A1vlJZgQ` showed `PROD_CORRELATION ERROR` in the preview and was accepted
    the moment it was submitted. Deferring instead blocked 180 alphas over
    4.5 hours and produced nothing. A fetch error still must not be recorded as
    a FAIL: that would retire the alpha on a platform-side condition.
    """
    _seed(conn, "UNKNOWN", 3.0)
    submitted = []
    monkeypatch.setattr(
        auto_check, "check_and_submit", lambda session, c, aid: submitted.append(aid) or "CHECK_UNAVAILABLE"
    )
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == ["UNKNOWN"]
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='UNKNOWN'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM submission_checks WHERE alpha_id='UNKNOWN'").fetchone()[0] == 0
