"""Uncertain mutation outcomes retain request ownership across restarts."""

from types import SimpleNamespace

import pytest

from core.db import connect, init_tables
from storage.submission_requests import begin_request, needs_reconciliation, record_response


def test_accepted_request_survives_reopen_and_is_never_reposted(tmp_path, monkeypatch):
    from runner import verify_submit
    from runner.submit import flow

    path = tmp_path / "requests.duckdb"
    conn = connect(path)
    init_tables(conn)
    conn.execute("INSERT INTO alpha_results (alpha_id,status,raw_json) VALUES ('A','UNSUBMITTED','{}')")
    conn.commit()
    posts, gets = [], []
    monkeypatch.setattr(flow, "ensure_description", lambda *args: None)
    monkeypatch.setattr(flow, "try_submit", lambda *args: (posts.append("POST") or 201, None))
    monkeypatch.setattr(verify_submit, "VERIFY_MAX_WAIT_SEC", 0)

    def observe(*args):
        gets.append("GET")
        return (200, None, "UNSUBMITTED") if len(gets) == 1 else (200, "2026-10-18T09:51:57Z", "ACTIVE")

    monkeypatch.setattr(verify_submit, "_get_alpha", observe)
    assert flow.check_and_submit(None, conn, "A") == "PENDING"
    conn.close()
    conn = connect(path)
    assert needs_reconciliation(conn, "A")
    assert flow.check_and_submit(None, conn, "A") == "SUBMITTED"
    assert posts == ["POST"]
    assert gets == ["GET", "GET"]
    assert conn.execute("SELECT state FROM submission_requests").fetchone()[0] == "VERIFIED"
    conn.close()


@pytest.mark.parametrize("code", [403, 429])
def test_explicit_rejection_releases_request(code):
    conn = connect(":memory:")
    begin_request(conn, "A")
    record_response(conn, "A", code)
    assert not needs_reconciliation(conn, "A")
    conn.close()


def test_two_connections_cannot_claim_the_same_request(tmp_path):
    first = connect(tmp_path / "claims.duckdb")
    second = connect(tmp_path / "claims.duckdb")
    assert begin_request(first, "A")
    assert not begin_request(second, "A")
    record_response(first, "A", 403)
    assert begin_request(second, "A")
    second.close()
    first.close()


def test_pending_request_bypasses_preview_and_reconciles(monkeypatch):
    from checker.auto_check_alpha import _check_alpha

    conn = connect(":memory:")
    begin_request(conn, "A", http_status=201)
    calls = []
    _check_alpha(
        None,
        conn,
        "A",
        2.2,
        check_via_get=lambda *args: pytest.fail("An existing request needs reconciliation, not a new preview"),
        check_and_submit=lambda *args: calls.append("reconcile") or "PENDING",
    )
    assert calls == ["reconcile"]
    conn.close()


@pytest.mark.parametrize("failure", [TimeoutError("response lost"), 500])
def test_ambiguous_submit_response_is_not_retried(failure):
    from checker.check_via_submit import check_via_submit

    calls = []

    def post(*args, **kwargs):
        calls.append("POST")
        if isinstance(failure, Exception):
            raise failure
        return SimpleNamespace(status_code=failure, headers={}, text="server error")

    result = check_via_submit(SimpleNamespace(post=post), "A")
    assert result[0] in (None, 500)
    assert calls == ["POST"]
