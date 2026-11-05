"""Runtime authentication must not recover or persist database credentials."""

import json
from types import SimpleNamespace

import duckdb
import pytest

import core.auth as auth
import download.session as download_session
from core.auth_credentials import load_credentials


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch, tmp_path):
    for name in ("BRAIN_EMAIL", "BRAIN_PASSWORD", "BRAIN_CREDENTIALS_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(auth, "PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(download_session, "PROJECT_DIR", str(tmp_path))


def test_complete_environment_pair_takes_precedence_without_logging_values(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("BRAIN_EMAIL", "fixture@example.test")
    monkeypatch.setenv("BRAIN_PASSWORD", "fixture-environment-secret")
    session = SimpleNamespace(auth=None)
    assert load_credentials(session, tmp_path)
    assert session.auth == ("fixture@example.test", "fixture-environment-secret")
    assert "fixture-environment-secret" not in caplog.text


@pytest.mark.parametrize(
    "overrides",
    [
        {"BRAIN_EMAIL": "fixture@example.test"},
        {"BRAIN_PASSWORD": "fixture"},
        {"BRAIN_EMAIL": "", "BRAIN_PASSWORD": "fixture"},
    ],
)
def test_incomplete_environment_fails_closed(overrides, monkeypatch, tmp_path):
    (tmp_path / ".brain_credentials").write_text(json.dumps(["other@example.test", "other-fixture"]))
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)
    session = SimpleNamespace(auth=("stale", "stale"))
    assert not load_credentials(session, tmp_path)
    assert session.auth is None


def test_explicit_invalid_file_does_not_fall_back_to_another_account(monkeypatch, tmp_path):
    (tmp_path / ".brain_credentials").write_text(json.dumps(["other@example.test", "other-fixture"]))
    monkeypatch.setenv("BRAIN_CREDENTIALS_FILE", str(tmp_path / "missing.json"))
    assert not load_credentials(SimpleNamespace(auth=None), tmp_path)


def test_explicit_private_file(monkeypatch, tmp_path):
    path = tmp_path / "private.json"
    path.write_text(json.dumps(["fixture@example.test", "fixture-file-value"]))
    path.chmod(0o600)
    monkeypatch.setenv("BRAIN_CREDENTIALS_FILE", str(path))
    session = SimpleNamespace(auth=None)
    assert load_credentials(session, tmp_path)
    assert session.auth == ("fixture@example.test", "fixture-file-value")


@pytest.mark.parametrize("route", ["core", "download"])
def test_existing_legacy_database_is_never_opened_for_auth(route, monkeypatch, tmp_path):
    path = tmp_path / "legacy.duckdb"
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE TABLE credentials(key VARCHAR, value VARCHAR)")
        conn.execute(
            "INSERT INTO credentials VALUES (?, ?), (?, ?)",
            ["email", "fixture@example.test", "password", "fixture-db-value"],
        )
    # Pin the old module attributes too: a regression reintroducing the legacy
    # fallback would find this fixture and must fail this test.
    monkeypatch.setattr(auth, "DB_PATH", str(path), raising=False)
    monkeypatch.setattr(download_session, "DB_PATH", str(path), raising=False)
    opened = []

    def forbidden(*args, **kwargs):
        opened.append(True)
        raise AssertionError("authentication must not open DuckDB")

    monkeypatch.setattr(duckdb, "connect", forbidden)
    if route == "core":
        assert not auth._load_credentials(SimpleNamespace(auth=None))
    else:
        session = download_session.BrainSession()
        with pytest.raises(SystemExit):
            session.authenticate()
    assert opened == []


def test_downloader_uses_the_shared_environment_loader(monkeypatch):
    monkeypatch.setenv("BRAIN_EMAIL", "fixture@example.test")
    monkeypatch.setenv("BRAIN_PASSWORD", "fixture-download-value")
    session = download_session.BrainSession()
    monkeypatch.setattr(
        session.session, "post", lambda url: SimpleNamespace(status_code=201, json=lambda: {"user": {"id": "fixture"}})
    )
    session.authenticate()
    assert session.session.auth == ("fixture@example.test", "fixture-download-value")


def test_normal_schema_does_not_create_a_credential_store():
    from core.db import connect, init_tables

    conn = connect(":memory:")
    try:
        init_tables(conn)
        assert not conn.execute("SELECT 1 FROM information_schema.tables WHERE table_name='credentials'").fetchone()
    finally:
        conn.close()
