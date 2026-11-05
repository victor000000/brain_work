"""FIX 11: children/expr mismatch handling that never mis-attributes results."""

from runner import poll_children as pc
from tests.test_runner_fixes.helpers import batch_info
from tests.test_runner_fixes.test_outcome_and_children_helpers import parent


def test_too_few_children_stores_nothing_and_marks_mismatch(monkeypatch, conn):
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)
    parent(conn)
    info = batch_info(pid="P1", idx=1, exprs=("a", "b"))

    ok, err, complete = pc.handle_children(None, info, ["c1"], conn, info["settings"], "now")

    assert (ok, err, complete) == (0, 1, False)
    assert conn.execute("SELECT COUNT(*) FROM simulations WHERE parent_id='P1'").fetchone()[0] == 0
    msg = conn.execute("SELECT error_message FROM simulations WHERE sim_id='P1'").fetchone()[0]
    assert "mismatch" in msg


def test_too_many_children_processes_prefix_only(monkeypatch, conn):
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)
    fetched = []
    monkeypatch.setattr(
        pc,
        "fetch_child",
        lambda session, info, child_id, i, total, expr, c, s, now: (fetched.append(child_id), (1, 0, True))[1],
    )
    info = batch_info(pid="P1", idx=1, exprs=("a", "b"))

    ok, err, complete = pc.handle_children(None, info, ["c1", "c2", "c3"], conn, info["settings"], "now")

    assert fetched == ["c1", "c2"]  # extras are not attributed to an expression
    assert (ok, err, complete) == (2, 1, True)


def test_equal_length_children_all_fetched(monkeypatch, conn):
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)
    monkeypatch.setattr(pc, "fetch_child", lambda *a: (1, 0, True))
    info = batch_info(pid="P1", idx=1, exprs=("a", "b"))

    assert pc.handle_children(None, info, ["c1", "c2"], conn, info["settings"], "now") == (2, 0, True)


def test_unfetched_child_keeps_batch_incomplete(monkeypatch, conn):
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)
    monkeypatch.setattr(pc, "fetch_child", lambda *a: (0, 1, False))
    info = batch_info(pid="P1", idx=1, exprs=("a", "b"))

    assert pc.handle_children(None, info, ["c1", "c2"], conn, info["settings"], "now") == (0, 2, False)
