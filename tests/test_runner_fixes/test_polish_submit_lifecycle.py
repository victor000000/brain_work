"""Polish allowances count accepted or uncertain work, not definite rejections.

Exercise the real queue -> generation -> submit -> retry path with an in-memory
database and HTTP fakes. No network or production budget state is touched.
"""

import json

import pytest

import core.api_retry as api_retry
import core.budget as budget
from runner.explore_helpers import generate
from tests.test_api_retry_helpers import FakeResponse, FakeSession, clean_budget  # noqa: F401


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(api_retry.time, "sleep", lambda _seconds: None)


def _candidate(conn):
    conn.execute(
        "INSERT INTO alpha_results "
        "(alpha_id, expression, region, universe, delay, neutralization, decay, truncation) "
        "VALUES ('A1', 'rank(close)', 'HKG', 'TOP800', 1, 'SLOW', 8, 0.1)"
    )
    conn.execute(
        "INSERT INTO polish_candidates "
        "(alpha_id, expression, region, universe, delay, neutralization, created_at) "
        "VALUES ('A1', 'rank(close)', 'HKG', 'TOP800', 1, 'SLOW', 'now')"
    )
    conn.commit()


def _claim(conn):
    return conn.execute("SELECT attempts, tried FROM polish_candidates WHERE alpha_id='A1'").fetchone()


def test_python_refinement_preserves_language_lookback_and_other_settings(conn, monkeypatch):
    _candidate(conn)
    original = {
        "instrumentType": "EQUITY",
        "region": "HKG",
        "universe": "TOP800",
        "delay": 1,
        "language": "PYTHON",
        "lookback": 59,
        "decay": 8,
        "truncation": 0.1,
        "neutralization": "SLOW",
        "testPeriod": "P1Y0M",
        "maxTrade": "ON",
        "maxPosition": "OFF",
        "pasteurization": "ON",
        "nanHandling": "OFF",
    }
    conn.execute(
        "UPDATE alpha_results SET raw_json=? WHERE alpha_id='A1'", [json.dumps({"_submitted_settings": original})]
    )

    def forbid_random_settings(*args, **kwargs):
        raise AssertionError("Python refinement must not call FASTEXPR settings factory")

    monkeypatch.setattr(generate, "make_settings", forbid_random_settings)
    session = FakeSession([FakeResponse(400, text="rejected by fake server")])
    generate.generate_and_submit(session, conn, 4)
    submitted = session.calls[0][1]["settings"]
    assert submitted["neutralization"] != original["neutralization"]
    assert {k: v for k, v in submitted.items() if k != "neutralization"} == {
        k: v for k, v in original.items() if k != "neutralization"
    }
    assert _claim(conn) == (0, "")


def test_four_concurrent_rejections_leave_the_candidate_available(conn):
    _candidate(conn)
    session = FakeSession([FakeResponse(429, text="CONCURRENT_LIMIT reached") for _ in range(4)])

    for _ in range(4):
        assert generate.generate_and_submit(session, conn, 2) == "CONCURRENT"

    assert len(session.calls) == 4
    assert _claim(conn) == (0, "")
    assert conn.execute("SELECT COUNT(*) FROM simulations").fetchone()[0] == 0


def test_budget_exhausted_between_claim_and_post_refunds_without_posting(conn, monkeypatch):
    _candidate(conn)
    calls = []

    def exhaustion():
        calls.append(True)
        # The generator and finite-probe guard both run before claiming polish.
        return len(calls) > 2

    monkeypatch.setattr(budget, "is_exhausted", exhaustion)
    session = FakeSession([])
    assert generate.generate_and_submit(session, conn, 2) == "BUDGET"
    assert session.calls == []
    assert _claim(conn) == (0, "")


@pytest.mark.parametrize(
    ("response", "outcome"),
    [
        (FakeResponse(400, text="invalid settings"), None),
        (FakeResponse(429, {"X-Ratelimit-Reset": "900"}), "BUDGET"),
    ],
)
def test_definite_rejection_releases_both_attempt_and_tried_entry(conn, response, outcome):
    _candidate(conn)
    session = FakeSession([response])
    assert generate.generate_and_submit(session, conn, 2) == outcome
    assert len(session.calls) == 1
    assert _claim(conn) == (0, "")


def test_accepted_batch_keeps_attempt_and_is_stored(conn):
    _candidate(conn)
    session = FakeSession([FakeResponse(201, {"Location": "/simulations/P1", "X-Ratelimit-Remaining": "10"})])
    result = generate.generate_and_submit(session, conn, 2)
    assert result["pid"] == "P1"
    assert result["budget_low"] is False
    assert budget.is_exhausted() is False
    assert _claim(conn)[0] == 1
    assert _claim(conn)[1]
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone() == ("SUBMITTED",)


@pytest.mark.parametrize("status", [201, 200, 202, 408])
def test_unclear_acceptance_without_location_keeps_attempt(conn, status):
    _candidate(conn)
    session = FakeSession([FakeResponse(status)])
    assert generate.generate_and_submit(session, conn, 2) is None
    assert len(session.calls) == 1
    assert _claim(conn)[0] == 1
    assert _claim(conn)[1]


@pytest.mark.parametrize("first", [ConnectionError("response lost"), FakeResponse(503)])
@pytest.mark.parametrize(
    "last",
    [
        FakeResponse(400),
        FakeResponse(429, text="CONCURRENT_LIMIT"),
        FakeResponse(429, {"X-Ratelimit-Reset": "900"}),
    ],
)
def test_ambiguous_first_post_cannot_reach_a_later_rejection_or_refund(conn, first, last):
    _candidate(conn)
    session = FakeSession([first, last])
    assert generate.generate_and_submit(session, conn, 2) is None
    assert len(session.calls) == 1
    assert _claim(conn)[0] == 1
    assert _claim(conn)[1]


def test_only_rate_limited_attempts_release_after_retries_end(conn):
    _candidate(conn)
    session = FakeSession([FakeResponse(429, {"Retry-After": "1"}) for _ in range(api_retry.MAX_RETRIES)])
    assert generate.generate_and_submit(session, conn, 2) is None
    assert len(session.calls) == api_retry.MAX_RETRIES
    assert _claim(conn) == (0, "")


def test_settings_failure_before_post_releases_the_claim(conn, monkeypatch):
    _candidate(conn)

    def fail_settings(*_args, **_kwargs):
        raise ValueError("no legal settings")

    monkeypatch.setattr(generate, "make_settings", fail_settings)
    session = FakeSession([])
    with pytest.raises(ValueError, match="no legal settings"):
        generate.generate_and_submit(session, conn, 2)
    assert session.calls == []
    assert _claim(conn) == (0, "")
