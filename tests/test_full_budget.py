"""Use the final credits without overlapping delayed simulation charges."""

import json
from unittest.mock import MagicMock

import pytest

import core.budget as budget
from core.budget import state_exhaustion
from runner.explore_loop import fill
from runner.probe_queue_store import claim_next_probe, enqueue_probe
from runner.settings_factory import make_settings
from tests.test_budget_helpers import isolated_budget_state  # noqa: F401
from tests.test_runner_fixes import conftest as runner_fixtures
from tests.test_runner_fixes.test_fill_backoff_helpers import make_state

conn = runner_fixtures.conn


@pytest.mark.parametrize("remaining", [1, 2, 9, 10, 49, 50])
def test_every_positive_allowance_remains_usable(remaining):
    budget.update_from_headers({"X-Ratelimit-Remaining": str(remaining), "X-Ratelimit-Reset": "3600"})
    assert not budget.is_exhausted()
    assert budget.submission_capacity(10) == min(remaining, 10)


def test_last_accepted_simulation_parks_until_reset_without_losing_next_day(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(state_exhaustion.time, "time", lambda: clock[0])
    budget.update_from_headers({"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": "3600"})
    assert budget.submission_capacity(10) == 0
    clock[0] += 3601
    assert budget.submission_capacity(10) == 10
    assert budget.get_state().last_remaining is None


@pytest.mark.parametrize("exhausted", [True, False])
def test_restart_does_not_carry_yesterdays_zero_into_a_new_day(tmp_path, monkeypatch, exhausted):
    path = tmp_path / "budget.json"
    path.write_text(json.dumps({"exhausted": exhausted, "reset_at": 1, "last_remaining": 0}))
    monkeypatch.setenv("BRAIN_BUDGET_STATE_PATH", str(path))
    state = budget.BudgetState(persist=True)
    state.load_persisted_state()
    assert state.submission_capacity(10) == 10


def test_tail_drains_accepted_batches_before_spending_again(monkeypatch):
    budget.get_state().note_remaining(60)
    generate = MagicMock()
    monkeypatch.setattr(fill, "generate_and_submit", generate)
    state = make_state(inflight=[{"pid": "already-paid"}])
    fill.fill_slots(None, state, None, max_concurrent=6)
    generate.assert_not_called()
    assert state["inflight"] == [{"pid": "already-paid"}]
    assert not state["budget_exhausted"]


def test_tail_spends_all_three_credits_one_at_a_time_and_keeps_the_last_parent(monkeypatch):
    budget.get_state().note_remaining(3)
    sizes = []

    def generate(session, conn, idx, *, max_expressions):
        sizes.append(max_expressions)
        remaining = budget.get_state().last_remaining - max_expressions
        budget.update_from_headers({"X-Ratelimit-Remaining": str(remaining), "X-Ratelimit-Reset": "3600"})
        return {"pid": f"P{idx}", "idx": idx, "budget_remaining": remaining, "budget_low": remaining == 0}

    monkeypatch.setattr(fill, "generate_and_submit", generate)
    monkeypatch.setattr(fill.time, "sleep", lambda _: None)
    state = make_state()
    for _ in range(3):
        fill.fill_slots(None, state, None, max_concurrent=6)
        assert len(state["inflight"]) == 1
        if not budget.is_exhausted():
            state["inflight"].clear()  # the poller finished the accepted parent
    assert sizes == [1, 1, 1]
    assert state["inflight"][0]["pid"] == "P2"
    assert state["budget_exhausted"] and budget.is_exhausted()


def test_a_larger_finite_experiment_stays_pending_when_only_one_credit_fits(conn, monkeypatch):
    from runner import probe_validation

    monkeypatch.setattr(probe_validation, "target_pools", lambda *args: ({"close", "volume"}, set(), set()))
    monkeypatch.setattr(probe_validation, "load_operator_names", lambda _: {"rank"})
    settings = make_settings("USA", "TOP3000", 1, neutralization="SLOW", decay=5, truncation=0.05)
    large, _ = enqueue_probe(conn, ["rank(close)", "rank(volume)"], settings, ["idea:a", "idea:b"])
    small, _ = enqueue_probe(conn, ["rank(close)"], settings, ["idea:a"])
    assert claim_next_probe(conn, max_expressions=1)["probe_id"] == small
    assert conn.execute("SELECT state FROM probe_batches WHERE probe_id=?", [large]).fetchone()[0] == "PENDING"


def test_real_submit_path_fits_and_tracks_the_final_single_simulation(conn, monkeypatch):
    from runner.explore_helpers import generate
    from tests.test_api_retry_helpers import FakeResponse, FakeSession

    budget.get_state().note_remaining(1)
    monkeypatch.setattr(generate, "pyramid3_weighted_pick", lambda *args: (("USA", "TOP3000", 1), "pv"))
    monkeypatch.setattr(generate.polish, "should_polish", lambda _: False)
    requested = []

    def expressions(c, region, delay, universe, count, **kwargs):
        requested.append(count)
        return [f"rank(close)+{index}" for index in range(count)]

    monkeypatch.setattr(generate, "generate", expressions)
    session = FakeSession([FakeResponse(201, {"Location": "/simulations/LAST", "X-Ratelimit-Remaining": "0"})])
    result = generate.generate_and_submit(session, conn, 1, max_expressions=1)
    assert requested == [1]
    assert result["pid"] == "LAST" and result["budget_low"]
    assert result["exprs"] == ["rank(close)+0"]
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='LAST'").fetchone()[0] == "SUBMITTED"
    assert generate.generate_and_submit(session, conn, 2) == "BUDGET"
    assert len(session.calls) == 1


def test_final_credit_reserves_only_one_polish_candidate(conn):
    import random

    from runner.explore_helpers.polish_queue import take_batch

    conn.executemany(
        "INSERT INTO polish_candidates (alpha_id,expression,region,universe,delay,neutralization,created_at) "
        "VALUES (?,?,'USA','TOP3000',1,'SLOW','now')",
        [(f"A{i}", f"rank(close)+{i}") for i in range(3)],
    )
    plan = take_batch(conn, random.Random(1), batch_idx=2, max_expressions=1)
    assert plan is not None and len(plan["expressions"]) == 1
    assert len(plan["claim_receipt"]["entries"]) == 1
    assert conn.execute("SELECT SUM(attempts) FROM polish_candidates").fetchone()[0] == 1
