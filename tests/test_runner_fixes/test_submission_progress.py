"""Async submission verdicts must be reconciled without another mutation."""

from types import SimpleNamespace

import pytest

from runner import verify_submit
from runner.submit.flow import check_and_submit
from storage.submission_requests import begin_request, needs_reconciliation
from tests.test_runner_fixes.helpers import FakeResponse


@pytest.fixture
def pending_owner(conn, monkeypatch):
    conn.execute("INSERT INTO alpha_results(alpha_id,status,raw_json) VALUES ('P1','UNSUBMITTED','{}')")
    conn.commit()
    begin_request(conn, "P1", http_status=201)
    clock = SimpleNamespace(now=0.0, sleeps=[])

    def sleep(seconds):
        assert seconds > 0
        clock.sleeps.append(seconds)
        clock.now += seconds

    monkeypatch.setattr(verify_submit.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(verify_submit.time, "sleep", sleep)
    return clock


def session_for(progress, *, submitted_after=None):
    calls = []
    alpha_gets = 0

    def get(url, **kwargs):
        nonlocal alpha_gets
        calls.append((url, kwargs))
        if url.endswith("/submit"):
            if isinstance(progress, Exception):
                raise progress
            return progress
        alpha_gets += 1
        submitted = submitted_after is not None and alpha_gets >= submitted_after
        return FakeResponse(
            200,
            json_data={
                "dateSubmitted": "2026-10-19T14:30:00Z" if submitted else None,
                "status": "ACTIVE" if submitted else "UNSUBMITTED",
            },
        )

    def post(*args, **kwargs):
        pytest.fail("An existing submission request must never be POSTed again")

    return SimpleNamespace(get=get, post=post), calls


def test_async_real_rejection_reconciles_owner_and_native_checks(conn, pending_owner):
    # Native KPmn87kN receipt: submit progress403, despite alpha metadata
    # staying UNSUBMITTED/null. Its self correlation with xA1eX91J is0.9406.
    checks = [{"name": "SELF_CORRELATION", "result": "FAIL", "limit": 0.7, "value": 0.9406}]
    session, calls = session_for(FakeResponse(403, json_data={"is": {"checks": checks}}))
    assert check_and_submit(session, conn, "P1") == "FAIL:1"
    assert not needs_reconciliation(conn, "P1")
    assert conn.execute("SELECT state FROM submission_requests WHERE alpha_id='P1'").fetchone()[0] == "REJECTED"
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='P1'").fetchone()[0] == "REJECTED"
    assert conn.execute("SELECT fail_count FROM alpha_check_summary WHERE alpha_id='P1'").fetchone()[0] == 1
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == ["P1", "submit"]


def test_async_quota_rejection_defers_without_retiring_alpha(conn, pending_owner):
    checks = [{"name": "REGULAR_SUBMISSION", "result": "FAIL", "limit": 4, "value": 4}]
    session, _ = session_for(FakeResponse(403, json_data={"is": {"checks": checks}}))
    assert check_and_submit(session, conn, "P1") == "QUOTA_BLOCKED"
    assert not needs_reconciliation(conn, "P1")
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='P1'").fetchone()[0] == "UNSUBMITTED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='P1'").fetchone()[0] == 0
    assert conn.execute("SELECT attempts FROM check_deferrals WHERE alpha_id='P1'").fetchone()[0] == 1


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(404),
        FakeResponse(500),
        FakeResponse(403, json_data={"is": {"checks": [{"name": "CLUSTER_TEST", "result": "ERROR"}]}}),
        FakeResponse(403, json_data={"is": {"checks": [{"name": "PROD_CORRELATION", "result": "PENDING"}]}}),
        FakeResponse(403, json_data={"is": {"checks": [{"name": "ALREADY_SUBMITTED", "result": "FAIL"}]}}),
        FakeResponse(403, json_data={"is": {"checks": "malformed"}}),
        FakeResponse(200, json_data={"is": {"checks": [{"name": "LOW_SHARPE", "result": "PASS"}]}}),
        TimeoutError("progress response lost"),
    ],
)
def test_missing_or_undecided_progress_never_releases_or_invents_acceptance(conn, pending_owner, response):
    session, _ = session_for(response)
    assert check_and_submit(session, conn, "P1") == "PENDING"
    assert needs_reconciliation(conn, "P1")
    assert conn.execute("SELECT status FROM alpha_results WHERE alpha_id='P1'").fetchone()[0] == "UNSUBMITTED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='P1'").fetchone()[0] == 0


def test_expired_progress_is_probed_only_once_and_never_reposted(conn, pending_owner):
    session, calls = session_for(FakeResponse(404))
    assert check_and_submit(session, conn, "P1") == "PENDING"
    assert sum(url.endswith("/submit") for url, _ in calls) == 1
    assert needs_reconciliation(conn, "P1")


def test_progress_retry_after_is_bounded_by_observation_deadline(conn, pending_owner):
    session, calls = session_for(FakeResponse(200, headers={"Retry-After": "120"}))
    assert check_and_submit(session, conn, "P1") == "PENDING"
    assert pending_owner.sleeps == [verify_submit.VERIFY_MAX_WAIT_SEC]
    assert sum(url.endswith("/submit") for url, _ in calls) == 1
    assert needs_reconciliation(conn, "P1")


def test_progress_success_requires_actual_native_submission_date(conn, pending_owner):
    session, calls = session_for(FakeResponse(200, headers={"Retry-After": "2"}), submitted_after=2)
    assert check_and_submit(session, conn, "P1") == "SUBMITTED"
    assert pending_owner.sleeps == [2]
    assert conn.execute("SELECT state FROM submission_requests WHERE alpha_id='P1'").fetchone()[0] == "VERIFIED"
    assert sum(url.endswith("/submit") for url, _ in calls) == 1


def test_stale_progress_cannot_downgrade_a_previously_verified_request(conn, pending_owner):
    conn.execute("UPDATE submission_requests SET state='VERIFIED' WHERE alpha_id='P1'")
    conn.commit()
    checks = [{"name": "SELF_CORRELATION", "result": "FAIL", "value": 0.94}]
    session, _ = session_for(FakeResponse(403, json_data={"is": {"checks": checks}}))
    assert check_and_submit(session, conn, "P1") == "PENDING"
    assert conn.execute("SELECT state FROM submission_requests WHERE alpha_id='P1'").fetchone()[0] == "VERIFIED"
    assert conn.execute("SELECT COUNT(*) FROM alpha_check_summary WHERE alpha_id='P1'").fetchone()[0] == 0


@pytest.mark.parametrize("header", ["0", "-5"])
def test_ready_progress_without_date_does_not_spin(conn, pending_owner, header):
    session, calls = session_for(FakeResponse(200, headers={"Retry-After": header}))
    assert check_and_submit(session, conn, "P1") == "PENDING"
    assert pending_owner.sleeps == [verify_submit.VERIFY_POLL_INTERVAL_SEC] * 3
    assert sum(url.endswith("/submit") for url, _ in calls) == 3
