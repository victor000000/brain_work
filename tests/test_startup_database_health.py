"""A broken optional cache may be skipped; an unusable connection may not."""

from unittest.mock import Mock

import pytest

import runner.explore_loop.startup as startup
import simulate_alphas as app
from core.db import connect
from core.db.health import UnusableConnectionError


def loaders(monkeypatch):
    failing = Mock(side_effect=RuntimeError("target refresh failed"))
    later = Mock()
    background = Mock()
    monkeypatch.setattr(startup, "refresh_quarter_targets", failing)
    for name in (
        "load_diversity_weights",
        "refresh_cell_yield_posterior",
        "load_cell_yield_posterior",
        "load_corr_prior",
    ):
        monkeypatch.setattr(startup, name, later)
    monkeypatch.setattr(startup.cell_priors, "load_priors", later)
    monkeypatch.setattr(startup, "start_background_check", background)
    return later, background


def test_invalid_connection_aborts_before_checks_or_other_loaders(monkeypatch):
    later, background = loaders(monkeypatch)
    conn = Mock()
    conn.execute.side_effect = RuntimeError("database has been invalidated")
    with pytest.raises(UnusableConnectionError):
        startup._startup_checks(object(), conn)
    later.assert_not_called()
    background.assert_not_called()


def test_healthy_connection_continues_after_optional_loader_failure(monkeypatch):
    later, background = loaders(monkeypatch)
    conn = connect(":memory:")
    try:
        startup._startup_checks(object(), conn)
        assert later.call_count == 5
        background.assert_called_once()
    finally:
        conn.close()


def test_entrypoint_exits_and_releases_invalid_connection_without_retry(monkeypatch):
    conn = Mock()
    loop = Mock(side_effect=UnusableConnectionError("invalidated"))
    session = Mock(return_value=object())
    monkeypatch.setattr(app, "get_conn", lambda: conn)
    monkeypatch.setattr(app, "init_tables", lambda _: None)
    monkeypatch.setattr(app, "_session_or_none", session)
    monkeypatch.setattr(app, "run_explore_loop", loop)
    assert app.main() == 1
    conn.close.assert_called_once()
    loop.assert_called_once()
    session.assert_called_once()
