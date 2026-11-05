"""A failed child fetch must never be reported as complete."""

from unittest.mock import MagicMock

from runner import poll_children_fetch as pcf
from storage.store_sim import store_sim
from tests.test_runner_fixes.helpers import batch_info, batch_settings


def test_child_fetch_failure_never_reports_complete(monkeypatch, conn):
    monkeypatch.setattr(pcf.time, "sleep", lambda *_: None)
    session = MagicMock()
    session.get.side_effect = RuntimeError("connection reset")
    info = batch_info(pid="P1", idx=1, exprs=("a",))

    assert pcf.fetch_child(session, info, "c1", 0, 1, "a", conn, info["settings"], "now") == (0, 1, False)


def test_already_stored_child_counts_as_fetched(monkeypatch, conn):
    monkeypatch.setattr(pcf.time, "sleep", lambda *_: None)
    store_sim(conn, "c1", "P1", 1, "a", "USA", "TOP3000", 1, "COMPLETE", "A1", None, batch_settings(), "now")
    conn.execute(
        "INSERT INTO alpha_results (alpha_id, sim_id, expression, region, universe, delay, status) "
        "VALUES ('A1', 'c1', 'a', 'USA', 'TOP3000', 1, 'UNSUBMITTED')"
    )
    conn.commit()
    session = MagicMock()
    session.get.side_effect = RuntimeError("connection reset")
    info = batch_info(pid="P1", idx=1, exprs=("a",))

    assert pcf.fetch_child(session, info, "c1", 0, 1, "a", conn, info["settings"], "now") == (0, 0, True)
