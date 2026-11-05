"""FIX 5: the GET /check preview gates the submission attempt — a FAIL stops
it, and a preview that cannot be read does not."""

from checker import auto_check
from tests.test_runner_fixes.auto_check_helpers import _gates_pass, _seed  # noqa: F401


def test_preview_fail_skips_the_submission_attempt(monkeypatch, conn):
    """A FAIL in the GET /check preview means the alpha cannot be accepted.

    Submitting it anyway spends a submission attempt and ends in a 403; the
    preview gate records the checks (draining the queue) and moves on.
    """
    _seed(conn, "WEAK", 3.0)
    monkeypatch.setattr(
        auto_check,
        "check_via_get",
        lambda session, aid: [{"name": "LOW_2Y_SHARPE", "result": "FAIL", "limit": 1.58, "value": 0.0}],
    )
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: submitted.append(aid) or "FAIL:1")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == []
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='WEAK'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM submission_checks WHERE alpha_id='WEAK'").fetchone()[0] == 1


def test_preview_without_fails_still_submits(monkeypatch, conn):
    _seed(conn, "HOPE", 3.0)
    monkeypatch.setattr(
        auto_check,
        "check_via_get",
        lambda session, aid: [
            {"name": "LOW_SHARPE", "result": "PASS", "limit": 1.58, "value": 2.2},
            {"name": "SELF_CORRELATION", "result": "PENDING"},
        ],
    )
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: submitted.append(aid) or "SUBMITTED")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == ["HOPE"]


def test_preview_unavailable_does_not_block_submission(monkeypatch, conn):
    """A preview that never resolves (None) must not stop a submission —
    the POST is the authoritative check."""
    _seed(conn, "MAYBE", 3.0)
    monkeypatch.setattr(auto_check, "check_via_get", lambda session, aid: None)
    submitted = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: submitted.append(aid) or "THROTTLED")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert submitted == ["MAYBE"]
