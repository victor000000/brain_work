"""FIX 1: a 201-accepted batch is always stored, even when the budget header is
absent or low; a low budget is reported via `budget_low`, never by discarding
the accepted batch."""

import json

from runner import submit_batch as sb
from tests.test_runner_fixes.helpers import FakeResponse, batch_settings


def _post_returning(resp):
    return lambda session, payload, batch_idx: resp


def test_201_without_budget_header_stores_parent(monkeypatch, conn):
    resp = FakeResponse(201, headers={"Location": "https://api.worldquantbrain.com/simulations/P1"})
    monkeypatch.setattr(sb, "post_simulation", _post_returning(resp))
    seen = []
    monkeypatch.setattr(sb, "update_from_headers", lambda headers: seen.append(headers))

    info = sb.submit_batch(None, ["rank(x)", "rank(y)"], batch_settings(), 3, conn)

    assert isinstance(info, dict)
    assert info["pid"] == "P1"
    assert info["budget_remaining"] is None
    assert info["budget_low"] is False  # unknown != exhausted
    row = conn.execute("SELECT status, expression, parent_id, batch_idx FROM simulations WHERE sim_id='P1'").fetchone()
    assert row[0] == "SUBMITTED"
    assert json.loads(row[1]) == ["rank(x)", "rank(y)"]
    assert row[2] is None
    assert row[3] == 3
    assert seen  # headers were still fed to the budget tracker


def test_201_with_low_budget_stores_parent_and_flags(monkeypatch, conn):
    resp = FakeResponse(
        201,
        headers={"Location": "https://api.worldquantbrain.com/simulations/P2", "X-Ratelimit-Remaining": "0"},
    )
    monkeypatch.setattr(sb, "post_simulation", _post_returning(resp))
    monkeypatch.setattr(sb, "update_from_headers", lambda headers: None)

    info = sb.submit_batch(None, ["rank(x)"], batch_settings(), 4, conn)

    assert isinstance(info, dict)  # not "BUDGET"
    assert info["budget_low"] is True
    assert info["budget_remaining"] == 0
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P2'").fetchone()[0] == "SUBMITTED"


def test_201_with_healthy_budget_is_not_flagged(monkeypatch, conn):
    resp = FakeResponse(
        201,
        headers={"Location": "https://api.worldquantbrain.com/simulations/P3", "X-Ratelimit-Remaining": "500"},
    )
    monkeypatch.setattr(sb, "post_simulation", _post_returning(resp))
    monkeypatch.setattr(sb, "update_from_headers", lambda headers: None)

    info = sb.submit_batch(None, ["rank(x)"], batch_settings(), 5, conn)

    assert info["budget_low"] is False
    assert info["budget_remaining"] == 500
    assert conn.execute("SELECT status FROM simulations WHERE sim_id='P3'").fetchone()[0] == "SUBMITTED"
