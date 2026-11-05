"""Probe lifecycle — accepted sims are always cancelled, failures are not rejections."""

import logging

import pytest

from tests.test_probe_combos_helpers import FakeSession, Resp, no_sleep  # noqa: F401
from tools.probe_simulation_combos import probe as probe_mod
from tools.probe_simulation_combos.probe import ACCEPTED_STATUSES, probe_combo


def test_accepted_201_with_location_is_cancelled():
    session = FakeSession([Resp(201, {"Location": "/simulations/abc"})])
    verdict, _detail = probe_combo(session, "USA", "TOP3000", 1)
    assert verdict == "OK"
    assert session.cancelled == ["https://api.worldquantbrain.com/simulations/abc"]


def test_accepted_202_is_cancelled_too():
    """202 used to be classified HTTP_202 and left running."""
    session = FakeSession([Resp(202, {"Location": "https://api.worldquantbrain.com/simulations/x"})])
    verdict, _detail = probe_combo(session, "USA", "TOP3000", 1)
    assert verdict == "HTTP_202"
    assert session.cancelled == ["https://api.worldquantbrain.com/simulations/x"]


def test_all_2xx_are_treated_as_accepted():
    assert {200, 201, 202} == ACCEPTED_STATUSES


def test_cancel_runs_when_classify_raises(monkeypatch):
    session = FakeSession([Resp(201, {"Location": "/simulations/boom"})])
    monkeypatch.setattr(probe_mod, "classify", lambda _r: (_ for _ in ()).throw(RuntimeError("classify bug")))
    with pytest.raises(RuntimeError):
        probe_combo(session, "USA", "TOP3000", 1)
    assert session.cancelled == ["https://api.worldquantbrain.com/simulations/boom"]


def test_cancel_runs_on_interrupt(monkeypatch):
    session = FakeSession([Resp(201, {"Location": "/simulations/intr"})])

    def interrupt(_r):
        raise KeyboardInterrupt

    monkeypatch.setattr(probe_mod, "classify", interrupt)
    with pytest.raises(KeyboardInterrupt):
        probe_combo(session, "USA", "TOP3000", 1)
    assert session.cancelled == ["https://api.worldquantbrain.com/simulations/intr"]


def test_rejected_400_is_not_cancelled():
    session = FakeSession([Resp(400, {}, body={"detail": "universe not available"})])
    verdict, _detail = probe_combo(session, "USA", "TOP3000", 99)
    assert verdict == "REJECT_NOT_AVAILABLE"
    assert session.cancelled == []


def test_accepted_without_location_warns_but_does_not_crash(caplog):
    session = FakeSession([Resp(201, {})])
    with caplog.at_level(logging.WARNING):
        verdict, _detail = probe_combo(session, "USA", "TOP3000", 1)
    assert verdict == "OK"
    assert session.cancelled == []
    assert "without a Location header" in caplog.text
