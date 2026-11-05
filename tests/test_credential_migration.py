"""Backup-before-clear maintenance using only synthetic credential databases."""

import json

import duckdb
import pytest

from core.credential_migration import MigrationError, exclusive_writer, export_legacy, remove_legacy


@pytest.fixture
def legacy(tmp_path):
    database = tmp_path / "legacy.duckdb"
    with duckdb.connect(str(database)) as conn:
        conn.execute("CREATE TABLE credentials(key VARCHAR, value VARCHAR)")
        conn.executemany(
            "INSERT INTO credentials VALUES (?, ?)",
            [
                ("email", "fixture@example.test"),
                ("password", "fixture-password"),
                ("old_api_key", "fixture-provider-key"),
            ],
        )
        conn.execute("CREATE TABLE business_data(id INTEGER)")
        conn.execute("INSERT INTO business_data VALUES (42)")
    return database, tmp_path / "explorer.lock", tmp_path / "private-export"


def exported(legacy):
    database, lock, output = legacy
    result = export_legacy(database, lock, output, "private-fixture-folder", "owner@example.test")
    return result, json.loads((output / "migration.json").read_text())


def receipt(legacy, manifest, **changes):
    _, _, output = legacy
    metadata = {
        "id": "fixture-drive-file",
        "size": str((output / "legacy_credentials.json").stat().st_size),
        "parent_ids": ["private-fixture-folder"],
        "shared": False,
        "permissions": [{"type": "user", "role": "owner", "emailAddress": "owner@example.test"}],
    }
    metadata.update(changes)
    path = output / "backup-receipt.json"
    path.write_text(json.dumps({"sha256": manifest["sha256"], "drive_metadata": metadata}))
    path.chmod(0o600)
    return path


def test_export_contains_only_credentials_and_preserves_business_data(legacy):
    database, _, output = legacy
    result, _ = exported(legacy)
    assert result["rows"] == 3
    assert (output.stat().st_mode & 0o777) == 0o700
    assert (output / "legacy_credentials.json").stat().st_mode & 0o777 == 0o600
    assert "fixture-password" not in (output / "migration.json").read_text()
    assert "business_data" not in (output / "legacy_credentials.json").read_text()
    with duckdb.connect(str(database)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM credentials").fetchone() == (3,)
        assert conn.execute("SELECT * FROM business_data").fetchone() == (42,)


def test_no_removal_without_verified_private_backup(legacy):
    database, lock, output = legacy
    exported(legacy)
    with pytest.raises(MigrationError, match="backup receipt required"):
        remove_legacy(database, lock, output / "migration.json")
    with duckdb.connect(str(database)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM credentials").fetchone() == (3,)


@pytest.mark.parametrize(
    "change",
    [
        {"shared": True},
        {"permissions": []},
        {"permissions": [{"role": "owner", "type": "user", "emailAddress": "wrong@example.test"}]},
        {"parent_ids": ["wrong-folder"]},
        {"size": "0"},
        {"id": ""},
    ],
)
def test_invalid_backup_readback_never_removes_values(legacy, change):
    database, lock, output = legacy
    _, manifest = exported(legacy)
    path = receipt(legacy, manifest, **change)
    with pytest.raises(MigrationError, match="Backup readback"):
        remove_legacy(database, lock, output / "migration.json", path)
    with duckdb.connect(str(database)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM credentials").fetchone() == (3,)


def test_verified_backup_allows_removal_and_private_login_file(legacy):
    database, lock, output = legacy
    _, manifest = exported(legacy)
    path = receipt(legacy, manifest)
    result = remove_legacy(database, lock, output / "migration.json", path)
    assert result == {"credential_table_removed": True, "exported_rows": 3}
    login = database.parent / ".brain_credentials"
    assert json.loads(login.read_text()) == ["fixture@example.test", "fixture-password"]
    assert login.stat().st_mode & 0o777 == 0o600
    with duckdb.connect(str(database)) as conn:
        assert conn.execute("SELECT * FROM business_data").fetchone() == (42,)
        assert not conn.execute("SELECT 1 FROM information_schema.tables WHERE table_name='credentials'").fetchone()


def test_changed_database_requires_a_new_export_and_backup(legacy):
    database, lock, output = legacy
    _, manifest = exported(legacy)
    path = receipt(legacy, manifest)
    with duckdb.connect(str(database)) as conn:
        conn.execute("UPDATE credentials SET value=? WHERE key='password'", ["changed-fixture-value"])
    with pytest.raises(MigrationError, match="changed since export"):
        remove_legacy(database, lock, output / "migration.json", path)
    with duckdb.connect(str(database)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM credentials").fetchone() == (3,)


def test_existing_valid_login_is_not_overwritten(legacy):
    database, lock, output = legacy
    login = database.parent / ".brain_credentials"
    login.write_text(json.dumps(["other@example.test", "other-fixture-value"]))
    _, manifest = exported(legacy)
    path = receipt(legacy, manifest)
    remove_legacy(database, lock, output / "migration.json", path)
    assert json.loads(login.read_text()) == ["other@example.test", "other-fixture-value"]


def test_modified_local_export_cannot_authorize_removal(legacy):
    database, lock, output = legacy
    _, manifest = exported(legacy)
    path = receipt(legacy, manifest)
    (output / "legacy_credentials.json").write_text(json.dumps({"changed": "fixture"}))
    with pytest.raises(MigrationError, match="export changed"):
        remove_legacy(database, lock, output / "migration.json", path)


def test_missing_database_is_not_recreated_by_removal(legacy):
    database, lock, output = legacy
    _, manifest = exported(legacy)
    path = receipt(legacy, manifest)
    database.unlink()
    with pytest.raises(MigrationError, match="does not exist"):
        remove_legacy(database, lock, output / "migration.json", path)
    assert not database.exists()


def test_remove_also_respects_the_live_writer_lock(legacy, monkeypatch):
    database, lock, output = legacy
    _, manifest = exported(legacy)
    path = receipt(legacy, manifest)
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("must not compete with a live writer")

    monkeypatch.setattr(duckdb, "connect", forbidden)
    with exclusive_writer(lock), pytest.raises(MigrationError, match="no database connection was attempted"):
        remove_legacy(database, lock, output / "migration.json", path)
    assert attempted == []


def test_active_writer_blocks_export_before_database_connection(legacy, monkeypatch):
    database, lock, output = legacy
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("must not compete with a live database writer")

    monkeypatch.setattr(duckdb, "connect", forbidden)
    with exclusive_writer(lock), pytest.raises(MigrationError, match="no database connection was attempted"):
        export_legacy(database, lock, output, "private-fixture-folder", "owner@example.test")
    assert attempted == []


@pytest.mark.parametrize("empty_table", [False, True])
def test_no_secret_rows_needs_no_credential_upload(tmp_path, empty_table):
    database = tmp_path / "empty.duckdb"
    lock, output = tmp_path / "writer.lock", tmp_path / "empty-export"
    with duckdb.connect(str(database)) as conn:
        conn.execute("CREATE TABLE business_data(id INTEGER)")
        if empty_table:
            conn.execute("CREATE TABLE credentials(key VARCHAR, value VARCHAR)")
    assert export_legacy(database, lock, output, "fixture-folder", "owner@example.test")["rows"] == 0
    assert not (output / "legacy_credentials.json").exists()
    assert remove_legacy(database, lock, output / "migration.json")["credential_table_removed"]
