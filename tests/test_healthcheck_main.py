"""`tools.healthcheck.__main__` exit status and missing-DB behaviour."""

from core.db import connect

# ── exit status / missing DB ──────────────────────────────────────


def test_main_does_not_create_a_missing_db(tmp_path, monkeypatch, capsys):
    from tools.healthcheck import __main__ as hc_main

    missing = tmp_path / "nope.db"
    monkeypatch.setattr(hc_main, "DB_PATH", str(missing))
    assert hc_main.main() == 1
    assert not missing.exists()


def test_main_returns_nonzero_when_a_check_fails(tmp_path, monkeypatch, capsys):
    from tools.healthcheck import __main__ as hc_main

    db = tmp_path / "ok.db"
    connect(db).close()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    for i in range(10):
        (log_dir / f"{i}.log").touch()

    monkeypatch.setattr(hc_main, "DB_PATH", str(db))
    monkeypatch.setattr(hc_main, "LOG_DIR", str(log_dir))
    for name in (
        "check_database",
        "check_integrity",
        "check_templates",
        "check_results",
        "check_alpha_recency",
        "check_explorer_progress",
        "check_processes",
    ):
        monkeypatch.setattr(hc_main, name, lambda *a, **k: True)
    monkeypatch.setattr(hc_main, "check_scope", lambda *a, **k: False)
    monkeypatch.setattr(hc_main, "check_field_freshness", lambda *a, **k: True)
    monkeypatch.setattr(hc_main, "check_generator", lambda *a, **k: True)

    assert hc_main.main() == 1
    assert "SOME CHECKS FAILED" in capsys.readouterr().out


def test_main_returns_zero_when_all_checks_pass(tmp_path, monkeypatch):
    from tools.healthcheck import __main__ as hc_main

    db = tmp_path / "ok.db"
    connect(db).close()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    for i in range(10):
        (log_dir / f"{i}.log").touch()

    monkeypatch.setattr(hc_main, "DB_PATH", str(db))
    monkeypatch.setattr(hc_main, "LOG_DIR", str(log_dir))
    for name in (
        "check_database",
        "check_integrity",
        "check_scope",
        "check_field_freshness",
        "check_templates",
        "check_generator",
        "check_results",
        "check_alpha_recency",
        "check_explorer_progress",
        "check_processes",
    ):
        monkeypatch.setattr(hc_main, name, lambda *a, **k: True)

    assert hc_main.main() == 0


def test_healthcheck_imports_without_creating_state():
    """`python3 -m tools.healthcheck` must keep working (module-level import)."""
    import importlib

    mod = importlib.import_module("tools.healthcheck.__main__")
    assert callable(mod.main)


# The held-write-lock case lives in `test_healthcheck_locked.py`.
