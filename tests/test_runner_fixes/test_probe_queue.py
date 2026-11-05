"""Finite probes use real submission bookkeeping and survive interrupted POSTs."""

import json

import pytest

import core.api_retry as api_retry
import core.budget as budget
from core.db import init_tables
from generator.weighted_selection import peek_expr_template
from runner import probe_queue, probe_validation
from runner.explore_helpers.generate import generate_and_submit
from runner.explore_loop.fill import fill_slots
from runner.explore_loop.state import _initial_state
from runner.probe_queue_store import claim_next_probe, enqueue_probe
from runner.settings_factory import make_settings
from tests.test_api_retry_helpers import FakeResponse, FakeSession, clean_budget  # noqa: F401


@pytest.fixture(autouse=True)
def _offline_pools(monkeypatch):
    monkeypatch.setattr(api_retry.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(probe_validation, "target_pools", lambda *args: ({"close", "volume"}, set(), set()))
    monkeypatch.setattr(probe_validation, "load_operator_names", lambda _conn: {"rank", "ts_zscore"})


def _enqueue(conn, expression="rank(close)"):
    settings = make_settings("USA", "TOP3000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    return enqueue_probe(conn, [expression], settings, ["idea:test"])[0]


def _state(conn, probe_id):
    return conn.execute("SELECT state, parent_id FROM probe_batches WHERE probe_id=?", (probe_id,)).fetchone()


def _accepted(parent="P1", **headers):
    return FakeResponse(201, {"Location": f"/simulations/{parent}", **headers})


def test_queued_probe_precedes_random_generation_and_preserves_provenance(conn):
    probe_id = _enqueue(conn)
    session = FakeSession([_accepted()])
    result = generate_and_submit(session, conn, 1)

    assert result["pid"] == "P1"
    assert _state(conn, probe_id) == ("SUBMITTED", "P1")
    assert peek_expr_template("rank(close)") == "idea:test"
    row = conn.execute("SELECT status, expression FROM simulations WHERE sim_id='P1'").fetchone()
    assert row[0] == "SUBMITTED"
    assert json.loads(row[1]) == ["rank(close)"]
    assert probe_queue.submit_queued_probe(session, conn, 2) == (False, None)
    assert len(session.calls) == 1


def test_selected_probe_never_consumes_another_owner(conn):
    from tools.submit_selected_probe import submit_selected

    first = _enqueue(conn)
    selected = _enqueue(conn, "rank(volume)")
    session = FakeSession([_accepted()])
    assert submit_selected(session, conn, selected)["result"]["pid"] == "P1"
    assert _state(conn, first) == ("PENDING", None)
    assert _state(conn, selected) == ("SUBMITTED", "P1")
    assert submit_selected(session, conn, selected)["handled"] is False
    assert submit_selected(session, conn, "missing")["handled"] is False
    assert len(session.calls) == 1


def test_selected_probe_preserves_uncertainty_and_other_pending_work(conn):
    from tools.submit_selected_probe import submit_selected

    first = _enqueue(conn)
    selected = _enqueue(conn, "rank(volume)")
    conn.execute("UPDATE probe_batches SET state='UNCERTAIN' WHERE probe_id=?", (selected,))
    session = FakeSession([])
    assert submit_selected(session, conn, selected)["handled"] is False
    assert _state(conn, first) == ("PENDING", None)
    assert _state(conn, selected) == ("UNCERTAIN", None)
    assert not session.calls


def test_selected_probe_cli_refuses_competing_writer(monkeypatch, tmp_path):
    import fcntl

    from tools import submit_selected_probe as tool

    monkeypatch.setattr(tool, "LOG_DIR", str(tmp_path))
    monkeypatch.setattr(tool.sys, "argv", ["submit_selected_probe", "--probe-id", "P1", "--execute"])

    def forbidden():
        pytest.fail("competing command opened the database")

    monkeypatch.setattr(tool, "get_conn", forbidden)
    with (tmp_path / "explorer.lock").open("a") as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            tool.main()


def test_selected_poll_recovers_old_parent_without_post(conn, monkeypatch):
    from tools import submit_selected_probe as tool

    selected = _enqueue(conn)
    session = FakeSession([_accepted("old-parent")])
    tool.submit_selected(session, conn, selected)
    conn.execute("UPDATE simulations SET submitted_at='2020-01-01 00:00:00 UTC'")
    polled = []

    def observe(_session, info, _conn):
        polled.append(info)
        info["retry_after"] = 60
        return False

    monkeypatch.setattr(tool, "poll_batch", observe)
    result = tool.poll_selected(session, conn, selected)
    assert result["poll_complete"] is False
    assert result["next_poll_after_seconds"] == 60
    assert polled[0]["pid"] == "old-parent"
    assert polled[0]["exprs"] == ["rank(close)"]
    assert polled[0]["submitted_at"] < 1600000000
    assert _state(conn, selected) == ("SUBMITTED", "old-parent")
    assert len(session.calls) == 1


def test_selected_poll_requires_matching_receipt_and_skips_complete(conn, monkeypatch):
    from tools import submit_selected_probe as tool

    selected = _enqueue(conn)
    session = FakeSession([_accepted("P1")])
    with pytest.raises(ValueError, match="no stored parent"):
        tool.poll_selected(session, conn, selected)
    tool.submit_selected(session, conn, selected)

    def forbidden(*args):
        pytest.fail("unexpected polling")

    monkeypatch.setattr(tool, "poll_batch", forbidden)
    conn.execute("UPDATE simulations SET status='COMPLETE' WHERE sim_id='P1'")
    assert tool.poll_selected(session, conn, selected)["stored_status"] == "COMPLETE"
    conn.execute("UPDATE simulations SET expression='[\"rank(volume)\"]' WHERE sim_id='P1'")
    with pytest.raises(ValueError, match="payload differs"):
        tool.poll_selected(session, conn, selected)
    assert len(session.calls) == 1


def test_quota_parking_keeps_probe_pending_until_reset(conn):
    probe_id = _enqueue(conn)
    budget.mark_exhausted(3600)
    session = FakeSession([_accepted()])
    for idx in range(4):
        assert generate_and_submit(session, conn, idx) == "BUDGET"
    assert session.calls == []
    assert _state(conn, probe_id) == ("PENDING", None)

    budget.get_state().reset()
    assert generate_and_submit(session, conn, 1)["pid"] == "P1"
    assert _state(conn, probe_id) == ("SUBMITTED", "P1")


def test_definite_concurrent_rejection_preserves_probe_with_backoff(conn):
    probe_id = _enqueue(conn)
    session = FakeSession([FakeResponse(429, text="CONCURRENT_LIMIT"), _accepted()])
    assert probe_queue.submit_queued_probe(session, conn, 1) == (True, "CONCURRENT")
    assert _state(conn, probe_id) == ("PENDING", None)
    assert probe_queue.submit_queued_probe(session, conn, 2) == (False, None)
    assert len(session.calls) == 1
    conn.execute("UPDATE probe_batches SET retry_at=0")
    assert probe_queue.submit_queued_probe(session, conn, 3)[1]["pid"] == "P1"


def test_definite_client_rejection_cannot_starve_another_ready_probe(conn):
    first = _enqueue(conn)
    second = _enqueue(conn, "rank(volume)")
    conn.execute("UPDATE probe_batches SET created_at='2000-01-01' WHERE probe_id=?", (first,))
    session = FakeSession([FakeResponse(400, text="bad settings"), _accepted()])
    assert probe_queue.submit_queued_probe(session, conn, 1) == (True, None)
    assert _state(conn, first) == ("PENDING", None)
    assert conn.execute("SELECT retry_at FROM probe_batches WHERE probe_id=?", (first,)).fetchone()[0] > 0
    assert probe_queue.submit_queued_probe(session, conn, 2)[1]["pid"] == "P1"
    assert _state(conn, second) == ("SUBMITTED", "P1")


@pytest.mark.parametrize("status,text", [(429, "CONCURRENT_LIMIT"), (400, "bad settings")])
def test_elapsed_retry_delay_cannot_starve_untouched_probe(conn, monkeypatch, status, text):
    clock = [1000.0]
    monkeypatch.setattr(probe_queue.time, "time", lambda: clock[0])
    first = _enqueue(conn)
    second = _enqueue(conn, "rank(volume)")
    conn.execute("UPDATE probe_batches SET created_at='2000-01-01' WHERE probe_id=?", (first,))
    conn.execute("UPDATE probe_batches SET created_at='2001-01-01' WHERE probe_id=?", (second,))
    session = FakeSession([FakeResponse(status, text=text), _accepted("P2"), _accepted("P3")])
    probe_queue.submit_queued_probe(session, conn, 1)
    assert _state(conn, first) == ("PENDING", None)

    # The normal loop may sleep longer than the per-probe retry delay.
    clock[0] += 360
    assert probe_queue.submit_queued_probe(session, conn, 2)[1]["pid"] == "P2"
    assert _state(conn, second) == ("SUBMITTED", "P2")
    assert _state(conn, first) == ("PENDING", None)
    assert probe_queue.submit_queued_probe(session, conn, 3)[1]["pid"] == "P3"
    assert _state(conn, first) == ("SUBMITTED", "P3")
    assert len(session.calls) == 3


@pytest.mark.parametrize(
    "responses",
    [
        [ConnectionError("lost response")] * api_retry.MAX_RETRIES,
        [ConnectionError("lost response"), FakeResponse(429, text="CONCURRENT_LIMIT")],
        [FakeResponse(201)],
    ],
)
def test_ambiguous_post_is_held_instead_of_repeated_after_restart(conn, responses):
    probe_id = _enqueue(conn)
    session = FakeSession([*responses, _accepted()])
    probe_queue.submit_queued_probe(session, conn, 1)
    assert _state(conn, probe_id) == ("UNCERTAIN", None)
    sent = len(session.calls)
    assert sent == 1
    assert probe_queue.submit_queued_probe(session, conn, 2) == (False, None)
    assert len(session.calls) == sent


def test_crash_after_parent_store_reconciles_without_a_second_post(conn, monkeypatch):
    probe_id = _enqueue(conn)
    original = probe_queue.set_probe_state

    def interrupted(*_args, **_kwargs):
        raise RuntimeError("process interrupted before probe acknowledgment")

    monkeypatch.setattr(probe_queue, "set_probe_state", interrupted)
    session = FakeSession([_accepted()])
    with pytest.raises(RuntimeError, match="acknowledgment"):
        probe_queue.submit_queued_probe(session, conn, 1)
    assert _state(conn, probe_id) == ("CLAIMED", None)
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone() == ("SUBMITTED",)

    monkeypatch.setattr(probe_queue, "set_probe_state", original)
    assert probe_queue.submit_queued_probe(session, conn, 2) == (False, None)
    assert _state(conn, probe_id) == ("SUBMITTED", "P1")
    assert len(session.calls) == 1


def test_interrupted_claim_without_parent_is_not_assumed_unsent(conn):
    probe_id = _enqueue(conn)
    assert claim_next_probe(conn)["probe_id"] == probe_id
    session = FakeSession([])
    assert probe_queue.submit_queued_probe(session, conn, 1) == (False, None)
    assert _state(conn, probe_id) == ("UNCERTAIN", None)
    assert session.calls == []


def test_changed_field_availability_is_revalidated_before_post(conn, monkeypatch):
    probe_id = _enqueue(conn)
    monkeypatch.setattr(probe_validation, "target_pools", lambda *args: ({"volume"}, set(), set()))
    session = FakeSession([])
    assert probe_queue.submit_queued_probe(session, conn, 1) == (True, None)
    assert _state(conn, probe_id) == ("INVALID", None)
    assert "unknown field(s): close" in conn.execute("SELECT error_message FROM probe_batches").fetchone()[0]
    assert session.calls == []


def test_corrupt_payload_reaches_preflight_without_breaking_the_capacity_query(conn):
    probe_id = _enqueue(conn)
    conn.execute("UPDATE probe_batches SET expressions='not JSON' WHERE probe_id=?", [probe_id])
    session = FakeSession([])
    assert probe_queue.submit_queued_probe(session, conn, 1, max_expressions=1) == (True, None)
    assert _state(conn, probe_id) == ("INVALID", None)
    assert session.calls == []


def test_fill_loop_applies_the_same_concurrent_slot_limit_to_probes(conn):
    for offset in range(3):
        _enqueue(conn, f"rank(close)+{offset}")
    session = FakeSession([_accepted("P1"), _accepted("P2")])
    state = _initial_state()
    fill_slots(session, state, conn, max_concurrent=2)
    assert len(state["inflight"]) == len(session.calls) == 2
    assert conn.execute("SELECT COUNT(*) FROM probe_batches WHERE state='PENDING'").fetchone() == (1,)


def test_accepted_zero_budget_probe_stays_inflight_and_parks_next_probe(conn):
    for offset in range(2):
        _enqueue(conn, f"rank(close)+{offset}")
    session = FakeSession([_accepted("P1", **{"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": "900"})])
    state = _initial_state()
    fill_slots(session, state, conn, max_concurrent=6)
    assert [batch["pid"] for batch in state["inflight"]] == ["P1"]
    assert state["budget_exhausted"] is True
    assert len(session.calls) == 1
    assert conn.execute("SELECT COUNT(*) FROM probe_batches WHERE state='PENDING'").fetchone() == (1,)


def test_reenqueue_different_tag_does_not_replay_a_submitted_payload(conn):
    probe_id = _enqueue(conn)
    session = FakeSession([_accepted()])
    probe_queue.submit_queued_probe(session, conn, 1)
    settings = json.loads(conn.execute("SELECT settings FROM probe_batches").fetchone()[0])
    assert enqueue_probe(conn, ["rank(close)"], settings, ["idea:renamed"]) == (probe_id, False)
    init_tables(conn)
    assert _state(conn, probe_id) == ("SUBMITTED", "P1")


@pytest.mark.parametrize(
    ("expression", "override", "message"),
    [
        ("rank(assets)", {}, "unknown field"),
        ("rank(close)", {"region": "ALL", "universe": "LARGE"}, "not configured"),
        ("rank(close)", {"delay": True}, "not configured"),
        ("rank(close)", {"unitHandling": "OFF"}, "verify platform units"),
        ("rank(close)", {"decay": -1}, "invalid probe decay"),
        ("rank(close)", {"truncation": float("nan")}, "invalid probe truncation"),
        ("rank(close)", {"maxPosition": "INVALID"}, "must be ON or OFF"),
        ("rank(close)", {"maxTrade": "ON", "maxPosition": "ON"}, "cannot both be ON"),
        ("1", {}, "scoped data field"),
    ],
)
def test_invalid_probe_cannot_enter_the_queue(conn, expression, override, message):
    settings = make_settings("USA", "TOP3000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    settings.update(override)
    with pytest.raises(ValueError, match=message):
        enqueue_probe(conn, [expression], settings, ["idea:test"])
    assert conn.execute("SELECT COUNT(*) FROM probe_batches").fetchone() == (0,)


def test_unsupported_position_control_becomes_invalid_before_any_post(conn):
    settings = make_settings("KOR", "TOP600", 1, neutralization="INDUSTRY", decay=8, truncation=0.1)
    settings.update(maxTrade="OFF", maxPosition="OFF")
    probe_id = enqueue_probe(conn, ["rank(close)"], settings, ["idea:kor"])[0]
    # A plan queued by an older runner must also be rejected after deployment.
    settings["maxPosition"] = "ON"
    conn.execute("UPDATE probe_batches SET settings=? WHERE probe_id=?", [json.dumps(settings), probe_id])
    session = FakeSession([])
    assert probe_queue.submit_queued_probe(session, conn, 1) == (True, None)
    assert _state(conn, probe_id) == ("INVALID", None)
    assert "not available for region KOR" in conn.execute("SELECT error_message FROM probe_batches").fetchone()[0]
    assert session.calls == []


def test_supported_position_control_can_still_be_queued(conn):
    settings = make_settings("USA", "TOP3000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    settings.update(maxTrade="OFF", maxPosition="ON")
    probe_id = enqueue_probe(conn, ["rank(close)"], settings, ["idea:position"])[0]
    assert _state(conn, probe_id) == ("PENDING", None)
