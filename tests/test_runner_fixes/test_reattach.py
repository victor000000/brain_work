"""Startup recovery resumes unfinished parents, including partially stored batches."""

import time
from unittest.mock import MagicMock

from runner import poll_batch as pb
from runner.explore_loop.reattach import (
    REATTACH_MAX_AGE_SEC,
    find_orphan_batches,
)
from storage.store_sim import store_sim
from tests.test_runner_fixes.helpers import FakeResponse, batch_settings
from tests.test_runner_fixes.test_reattach_helpers import parent, ts


def test_orphan_found_with_reconstructed_location(conn):
    now = time.time()
    parent(conn, "P1", 7, ts(now))

    batches = find_orphan_batches(conn, limit=8, now=now)

    assert [b["pid"] for b in batches] == ["P1"]
    b = batches[0]
    assert b["loc"] == "https://api.worldquantbrain.com/simulations/P1"
    assert b["idx"] == 7
    assert b["exprs"] == ["rank(x)"]
    assert b["settings"]["region"] == "USA"
    assert b["reattached"] is True


def test_completed_child_with_missing_alpha_keeps_parent_recoverable(conn):
    now = time.time()
    parent(conn, "P1", 1, ts(now))
    store_sim(conn, "C1", "P1", 1, "rank(x)", "USA", "TOP3000", 1, "COMPLETE", "A1", None, batch_settings(), ts(now))

    assert [b["pid"] for b in find_orphan_batches(conn, limit=8, now=now)] == ["P1"]


def test_partially_stored_batch_is_recovered_and_finished(conn, monkeypatch):
    now = time.time()
    exprs = ("rank(x)", "rank(y)")
    parent(conn, "P1", 1, ts(now), exprs=exprs)
    store_sim(conn, "C1", "P1", 1, exprs[0], "USA", "TOP3000", 1, "COMPLETE", "A1", None, batch_settings(), ts(now))
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region) VALUES ('A1', 'C1', ?, 'USA')",
        (exprs[0],),
    )
    conn.commit()

    batches = find_orphan_batches(conn, limit=8, now=now)
    assert len(batches) == 1, "one fetched child must not strand the rest of its batch"

    bodies = {
        "simulations/P1": {"children": ["C1", "C2"]},
        "simulations/C1": {"status": "COMPLETE", "alpha": "A1"},
        "simulations/C2": {"status": "COMPLETE", "alpha": "A2"},
        "alphas/A1": {"id": "A1", "is": {"sharpe": 1.0}, "status": "UNSUBMITTED"},
        "alphas/A2": {"id": "A2", "is": {"sharpe": 2.0}, "status": "UNSUBMITTED"},
    }
    session = MagicMock()
    session.get.side_effect = lambda url, **kwargs: FakeResponse(json_data=bodies[url.split(".com/")[1]])
    monkeypatch.setattr("runner.poll_children.time.sleep", lambda *_: None)

    assert pb.poll_batch(session, batches[0], conn) is True
    assert conn.execute("SELECT alpha_id, expression FROM alpha_results ORDER BY alpha_id").fetchall() == [
        ("A1", exprs[0]),
        ("A2", exprs[1]),
    ]
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P1'").fetchone() == ("COMPLETE",)


def test_stored_alpha_excludes_parent(conn):
    now = time.time()
    parent(conn, "P1", 1, ts(now))
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay, status) "
        "VALUES ('A1', 'P1', 'rank(x)', 'USA', 'TOP3000', 1, 'UNSUBMITTED')"
    )
    conn.commit()

    assert find_orphan_batches(conn, limit=8, now=now) == []


def test_stale_and_terminal_parents_excluded(conn):
    now = time.time()
    parent(conn, "OLD", 1, ts(now - REATTACH_MAX_AGE_SEC - 60))
    parent(conn, "DONE", 2, ts(now), status="COMPLETE")

    assert find_orphan_batches(conn, limit=8, now=now) == []


def test_newest_first_and_limit(conn):
    now = time.time()
    parent(conn, "P1", 1, ts(now - 10))
    parent(conn, "P2", 2, ts(now - 5))
    parent(conn, "P3", 3, ts(now))

    batches = find_orphan_batches(conn, limit=2, now=now)

    assert [b["pid"] for b in batches] == ["P3", "P2"]
