"""The live writer ingests immutable plans without losing accepted ownership."""

import json

import pytest

import core.budget as budget
from core.db import connect, init_tables
from runner import probe_queue, probe_requests, probe_validation
from runner.explore_helpers.generate import generate_and_submit
from runner.explore_loop.fill import fill_slots
from runner.explore_loop.state import _initial_state
from runner.settings_factory import make_settings
from tests.test_api_retry_helpers import FakeResponse, FakeSession, clean_budget  # noqa: F401


@pytest.fixture
def conn():
    connection = connect(":memory:")
    init_tables(connection)
    yield connection
    connection.close()


@pytest.fixture(autouse=True)
def scoped_fields(monkeypatch):
    monkeypatch.setattr(probe_validation, "target_pools", lambda *args: ({"close", "volume"}, set(), set()))
    monkeypatch.setattr(probe_validation, "load_operator_names", lambda _conn: {"rank"})


def plan_file(tmp_path, expressions=("rank(close)",), decay=5, filename="plan.json"):
    settings = make_settings("USA", "TOP3000", 1, neutralization="SLOW", decay=decay, truncation=0.05)
    path = tmp_path / filename
    path.write_text(
        json.dumps(
            {
                "batches": [
                    {
                        "settings": settings,
                        "expressions": list(expressions),
                        "template_tags": ["probe:test"] * len(expressions),
                    }
                ]
            }
        )
    )
    return path


def test_cli_request_never_opens_the_database(tmp_path, monkeypatch, capsys):
    from tools import queue_probe_plan

    path = plan_file(tmp_path)
    monkeypatch.setattr(probe_requests, "LOG_DIR", str(tmp_path))
    monkeypatch.setattr(queue_probe_plan, "connect", lambda *a: pytest.fail("request opened a writer"))
    monkeypatch.setattr(queue_probe_plan, "connect_for_reading", lambda *a: pytest.fail("request opened a reader"))
    monkeypatch.setattr("sys.argv", ["queue_probe_plan", "--plan", str(path), "--request"])
    assert queue_probe_plan.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["requested"] is True
    assert not probe_requests.Path(result["receipt_path"]).exists()


def test_duplicate_requests_are_immutable_and_ingested_once(conn, tmp_path):
    path = plan_file(tmp_path)
    first = probe_requests.request_probe_plan(path, tmp_path / "inbox")
    assert probe_requests.request_probe_plan(path, tmp_path / "inbox") == first
    outcomes = probe_requests.ingest_probe_requests(conn, tmp_path / "inbox")
    assert outcomes[0]["state"] == "APPLIED"
    assert outcomes[0]["plan_sha256"] == first["plan_sha256"]
    assert probe_requests.ingest_probe_requests(conn, tmp_path / "inbox") == []
    assert conn.execute("SELECT COUNT(*) FROM probe_batches").fetchone()[0] == 1


def test_invalid_later_batch_cannot_partially_enqueue(conn, tmp_path):
    path = plan_file(tmp_path)
    document = json.loads(path.read_text())
    document["batches"].append({**document["batches"][0], "expressions": ["rank(unknown)"]})
    path.write_text(json.dumps(document))
    probe_requests.request_probe_plan(path, tmp_path / "inbox")
    result = probe_requests.ingest_probe_requests(conn, tmp_path / "inbox")
    assert result[0]["state"] == "REJECTED"
    assert "unknown field" in result[0]["error"]
    assert conn.execute("SELECT COUNT(*) FROM probe_batches").fetchone()[0] == 0


def test_receipt_failure_replays_without_resetting_an_accepted_probe(conn, tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    probe_requests.request_probe_plan(plan_file(tmp_path), inbox)
    original = probe_requests._atomic_write
    monkeypatch.setattr(
        probe_requests, "_atomic_write", lambda *a: (_ for _ in ()).throw(OSError("disk write interrupted"))
    )
    assert probe_requests.ingest_probe_requests(conn, inbox) == []
    conn.execute("UPDATE probe_batches SET state='SUBMITTED',parent_id='native-parent'")
    conn.commit()
    monkeypatch.setattr(probe_requests, "_atomic_write", original)
    receipt = probe_requests.ingest_probe_requests(conn, inbox)[0]
    assert receipt["state"] == "APPLIED"
    assert receipt["queue"][0]["inserted"] is False
    assert conn.execute("SELECT state,parent_id FROM probe_batches").fetchone() == ("SUBMITTED", "native-parent")


def test_partial_insert_retry_keeps_prior_claim_and_finishes_remaining_batches(conn, tmp_path, monkeypatch):
    path = plan_file(tmp_path)
    document = json.loads(path.read_text())
    document["batches"].append({**document["batches"][0], "expressions": ["rank(volume)"]})
    path.write_text(json.dumps(document))
    inbox = tmp_path / "inbox"
    probe_requests.request_probe_plan(path, inbox)
    original = probe_requests.enqueue_probe
    calls = []

    def interrupted(*args):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("interrupted after first commit")
        return original(*args)

    monkeypatch.setattr(probe_requests, "enqueue_probe", interrupted)
    assert probe_requests.ingest_probe_requests(conn, inbox) == []
    conn.execute("UPDATE probe_batches SET state='UNCERTAIN'")
    conn.commit()
    monkeypatch.setattr(probe_requests, "enqueue_probe", original)
    receipt = probe_requests.ingest_probe_requests(conn, inbox)[0]
    assert [row["inserted"] for row in receipt["queue"]] == [False, True]
    assert conn.execute("SELECT COUNT(*) FROM probe_batches WHERE state='UNCERTAIN'").fetchone()[0] == 1


def test_full_slots_ingest_without_polling_or_submitting(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(probe_requests, "LOG_DIR", str(tmp_path))
    probe_requests.request_probe_plan(plan_file(tmp_path))
    state = _initial_state()
    parent = {"pid": "existing-parent", "idx": 99}
    state["inflight"] = [parent]
    session = FakeSession([])
    fill_slots(session, state, conn, 1)
    assert state["inflight"] == [parent]
    assert state["batch_idx"] == 0
    assert session.calls == []
    assert conn.execute("SELECT COUNT(*) FROM probe_batches").fetchone()[0] == 1


def test_requested_plan_respects_budget_and_never_reposts_accepted_work(conn, tmp_path):
    inbox = tmp_path / "inbox"
    request = probe_requests.request_probe_plan(plan_file(tmp_path), inbox)
    probe_requests.ingest_probe_requests(conn, inbox)
    budget.mark_exhausted(3600)
    session = FakeSession([FakeResponse(201, {"Location": "/simulations/P1"})])
    assert generate_and_submit(session, conn, 0) == "BUDGET"
    assert session.calls == []
    budget.get_state().reset()
    assert generate_and_submit(session, conn, 1)["pid"] == "P1"
    probe_requests.Path(request["receipt_path"]).write_text("corrupt receipt")
    assert probe_requests.ingest_probe_requests(conn, inbox)[0]["queue"][0]["inserted"] is False
    assert probe_queue.submit_queued_probe(session, conn, 2) == (False, None)
    assert len(session.calls) == 1


def test_tampered_request_is_rejected_before_database_writes(conn, tmp_path):
    inbox = tmp_path / "inbox"
    request = probe_requests.request_probe_plan(plan_file(tmp_path), inbox)
    probe_requests.Path(request["request_path"]).write_text("{}")
    assert probe_requests.ingest_probe_requests(conn, inbox)[0]["state"] == "REJECTED"
    assert conn.execute("SELECT COUNT(*) FROM probe_batches").fetchone()[0] == 0


def test_ingestion_is_bounded_per_pass(conn, tmp_path):
    inbox = tmp_path / "inbox"
    for index in range(probe_requests.MAX_REQUESTS_PER_PASS + 1):
        probe_requests.request_probe_plan(plan_file(tmp_path, decay=index, filename=f"plan{index}.json"), inbox)
    assert len(probe_requests.ingest_probe_requests(conn, inbox)) == probe_requests.MAX_REQUESTS_PER_PASS
    assert len(probe_requests.ingest_probe_requests(conn, inbox)) == 1
