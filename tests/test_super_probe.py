"""Synthetic tests: never open production storage or use the native API."""

import json
from unittest.mock import Mock

import duckdb
import pytest

from runner import super_probe as probe


@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    probe.initialize(conn)
    yield conn
    conn.close()


def queued(db):
    return probe.enqueue(db, {"payload": {"type": "SUPER", "selection": "pv", "combo": "1"}})


def response(code, body, headers=None):
    result = Mock(status_code=code, headers=headers or {})
    result.json.return_value = body
    return result


@pytest.mark.parametrize(
    "code,location,state",
    [
        (201, "/simulations/abc", "SUBMITTED"),
        (201, None, "UNCERTAIN"),
        (201, "https://other.example/simulations/abc", "UNCERTAIN"),
        (500, None, "UNCERTAIN"),
        (429, None, "REJECTED"),
        (400, None, "REJECTED"),
    ],
)
def test_single_attempt_and_payload_dedup(db, code, location, state):
    owner = queued(db)
    session = Mock()

    def post(*args, **kwargs):
        assert probe.read(db, owner)["state"] == "CLAIMED"
        assert kwargs["allow_redirects"] is False
        return response(code, {}, {"Location": location} if location else {})

    session.post.side_effect = post
    assert probe.dispatch(db, owner, session, lambda: False)["state"] == state
    assert queued(db) == owner
    with pytest.raises(ValueError, match="already claimed"):
        probe.dispatch(db, owner, session, lambda: False)
    assert session.post.call_count == 1


def test_uncertain_transport_never_replays(db):
    owner = queued(db)
    session = Mock()
    session.post.side_effect = TimeoutError()
    assert probe.dispatch(db, owner, session, lambda: False)["state"] == "UNCERTAIN"
    with pytest.raises(ValueError):
        probe.dispatch(db, owner, session, lambda: False)


def test_zero_budget_does_not_claim(db):
    owner = queued(db)
    session = Mock()
    with pytest.raises(ValueError, match="exhausted"):
        probe.dispatch(db, owner, session, lambda: True)
    assert probe.read(db, owner)["state"] == "READY"
    session.post.assert_not_called()


def test_poll_delay_and_result_not_verified(db, monkeypatch):
    owner = queued(db)
    probe.save(db, owner, "SUBMITTED", [], probe.BASE + "/simulations/abc", 100)
    session = Mock()
    monkeypatch.setattr(probe.time, "time", lambda: 90)
    probe.poll(db, owner, session)
    session.get.assert_not_called()
    monkeypatch.setattr(probe.time, "time", lambda: 101)
    session.get.return_value = response(200, {"progress": 0.15}, {"Retry-After": "120"})
    assert probe.poll(db, owner, session)["next_poll"] == 221
    monkeypatch.setattr(probe.time, "time", lambda: 222)
    session.get.return_value = response(200, {"alpha": "alpha123"})
    row = probe.poll(db, owner, session)
    assert row["state"] == "RESULT_READY"
    assert json.loads(row["evidence"])[-1]["body"]["alpha"] == "alpha123"


def test_crash_claim_survives_reenqueue(db):
    owner = queued(db)
    probe.save(db, owner, "CLAIMED", [])
    assert queued(db) == owner
    with pytest.raises(ValueError):
        probe.dispatch(db, owner, Mock(), lambda: False)


@pytest.mark.parametrize("changed,expected", [(False, "VERIFIED_IDENTITY"), (True, "IDENTITY_MISMATCH")])
def test_result_identity_and_provenance(db, changed, expected):
    payload = {"type": "SUPER", "selection": "pv", "combo": "1", "settings": {"region": "HKG"}}
    owner = probe.enqueue(db, {"payload": payload})
    probe.save(db, owner, "RESULT_READY", [{"body": {"alpha": "abc"}}], probe.BASE + "/simulations/abc")
    session = Mock()
    native = {
        "id": "abc",
        "type": "SUPER",
        "selection": {"code": "pv"},
        "combo": {"code": "1"},
        "settings": {"region": "USA" if changed else "HKG"},
    }
    session.get.return_value = response(200, native)
    row = probe.fetch_result(db, owner, session)
    assert row["state"] == expected
    assert json.loads(row["evidence"])[-1]["body"] == native
    session.post.assert_not_called()


def test_result_transient_failure_keeps_owner(db):
    owner = queued(db)
    probe.save(db, owner, "RESULT_READY", [{"body": {"alpha": "abc"}}], probe.BASE + "/simulations/abc")
    session = Mock()
    session.get.return_value = response(503, {})
    assert probe.fetch_result(db, owner, session)["state"] == "RESULT_READY"
    session.post.assert_not_called()
