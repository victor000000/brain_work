"""FIX 5: checker selection uses the shared eligibility union and skips
terminal statuses and already-summarized alphas."""

import pytest

from checker import auto_check
from core.db import IntegrityError
from tests.test_runner_fixes.auto_check_helpers import _gates_pass, _seed  # noqa: F401


def test_a_null_summary_row_cannot_be_stored(conn):
    """`alpha_check_summary.alpha_id` is the primary key, so it is NOT NULL.

    Under SQLite a nullable TEXT PRIMARY KEY accepted a NULL row, which made
    the old `alpha_id NOT IN (SELECT alpha_id ...)` predicate NULL for every
    candidate and silently starved the check queue. DuckDB rejects that row at
    the schema level, so the failure mode cannot be constructed; the selector
    still uses NOT EXISTS (the safe form) and the neighbouring test pins that
    summarized alphas are skipped.
    """
    with pytest.raises(IntegrityError):
        conn.execute(
            "INSERT INTO alpha_check_summary (alpha_id, pass_count, fail_count, warn_count, pend_count, checked_at) "
            "VALUES (NULL, 0, 0, 0, 0, 'now')"
        )


def test_only_eligible_unchecked_unsubmitted_alphas_are_checked(monkeypatch, conn):
    _seed(conn, "OK", 3.0)
    _seed(conn, "SUB", 3.0, status="SUBMITTED")
    _seed(conn, "REJ", 3.0, status="REJECTED")
    _seed(conn, "SUMMED", 3.0, summary=True)
    _seed(conn, "LOW", 0.5)  # below the USA/d1 1.65 floor

    checked = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: checked.append(aid) or "FAIL:1")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert checked == ["OK"]


def test_out_of_scope_alphas_are_never_submitted(monkeypatch, conn):
    """Submission stays inside the pv/option scope: a legacy alpha built on a
    foreign category must not be auto-submitted even with a higher sharpe."""
    _seed(conn, "FOREIGN", 4.0, categories='["pv", "other"]')
    _seed(conn, "IN_SCOPE", 2.0)

    checked = []
    monkeypatch.setattr(auto_check, "check_and_submit", lambda session, c, aid: checked.append(aid) or "FAIL:1")
    monkeypatch.setattr(auto_check.time, "sleep", lambda *_: None)

    auto_check.check_new_alphas(None, conn, limit=20)

    assert checked == ["IN_SCOPE"]
