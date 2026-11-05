"""Budget parking must preserve the near-miss queue until simulations can run."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import core.budget as budget
from runner.explore_helpers.generate import generate_and_submit
from runner.explore_loop import sleep_logic


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


def test_exhausted_budget_preserves_polish_attempts(conn, monkeypatch):
    _candidate(conn)
    monkeypatch.setattr(budget, "is_exhausted", lambda: True)
    session = MagicMock()

    for batch_idx in (2, 6, 10, 14):
        assert generate_and_submit(session, conn, batch_idx) == "BUDGET"

    session.post.assert_not_called()
    assert conn.execute("SELECT attempts, tried FROM polish_candidates").fetchone() == (0, "")


def test_budget_reset_allows_the_preserved_candidate_to_run(conn, monkeypatch):
    _candidate(conn)
    exhausted = [True]
    monkeypatch.setattr(budget, "is_exhausted", lambda: exhausted[0])
    from runner.explore_helpers import generate

    submitted = []
    monkeypatch.setattr(
        generate,
        "submit_batch",
        lambda session, exprs, settings, idx, c, **_kwargs: submitted.append(exprs) or {"idx": idx},
    )

    assert generate_and_submit(None, conn, 2) == "BUDGET"
    assert submitted == []
    exhausted[0] = False
    assert generate_and_submit(None, conn, 2) == {"idx": 2}
    assert submitted == [["rank(close)"]]
    assert conn.execute("SELECT attempts FROM polish_candidates").fetchone() == (1,)


@pytest.mark.parametrize("still_exhausted", [True, False])
def test_budget_sleep_rechecks_exhaustion_at_wakeup(monkeypatch, still_exhausted):
    state = {"budget_exhausted": True, "inflight": []}
    waited = []
    monkeypatch.setattr(sleep_logic, "time", SimpleNamespace(sleep=waited.append))
    monkeypatch.setattr(budget, "seconds_until_reset", lambda: 3600)
    monkeypatch.setattr(budget, "is_exhausted", lambda: still_exhausted)

    sleep_logic.sleep_after_pass(state)

    assert waited == [sleep_logic.CHECK_MAX_IDLE_SEC]
    assert state["budget_exhausted"] is still_exhausted
