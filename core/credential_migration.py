"""Exclusive, backup-first removal of the legacy credential table.

Only this maintenance module reads legacy database credentials. Runtime auth
does not import it. Export files are private; no secret values are returned.
"""

import contextlib
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path

import duckdb

from core.auth_credentials import _valid_pair
from core.credential_compaction import CompactionError, compact_if_needed


class MigrationError(RuntimeError):
    """A migration precondition failed; never include secret input in messages."""

    def __init__(self, message, *, rollback_path=None):
        super().__init__(message)
        self.rollback_path = rollback_path


@contextlib.contextmanager
def exclusive_writer(lock_file):
    """Acquire the supervisor's lock before opening any database connection."""
    lock_file = Path(lock_file)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_file, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise MigrationError("Explorer owns the writer lock; no database connection was attempted") from None
        yield
    finally:
        os.close(descriptor)


def _write_private(path, data):
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def _private_json(path):
    path = Path(path)
    mode = path.stat().st_mode
    if path.is_symlink() or not stat.S_ISREG(mode) or mode & 0o077:
        raise MigrationError("Migration files must be private regular files")
    return json.loads(path.read_text(encoding="utf-8"))


def _legacy_values(conn):
    exists = conn.execute(
        "SELECT table_type FROM information_schema.tables WHERE lower(table_schema)='main' AND lower(table_name)='credentials'"
    ).fetchone()
    if not exists:
        return None
    if exists[0] != "BASE TABLE":
        raise MigrationError("Unsupported legacy credential relation; no values removed")
    columns = {row[0].lower() for row in conn.execute("DESCRIBE main.credentials").fetchall()}
    if columns != {"key", "value"}:
        raise MigrationError("Unsupported legacy credential schema; no values removed")
    values = {}
    for key, value in conn.execute('SELECT "key", "value" FROM main.credentials').fetchall():
        if not isinstance(key, str) or key in values or (value is not None and not isinstance(value, str)):
            raise MigrationError("Legacy credentials cannot be exported losslessly; no values removed")
        values[key] = value
    return values


def export_legacy(database, lock_file, output_directory, drive_folder_id, owner_email):
    """Export only the credential table; business tables are neither read nor copied."""
    database = Path(database).resolve()
    if not database.is_file():
        raise MigrationError("Database does not exist")
    output = Path(output_directory)
    with exclusive_writer(lock_file):
        with duckdb.connect(str(database), read_only=True) as conn:
            values = _legacy_values(conn)
        output.mkdir(mode=0o700, parents=True, exist_ok=True)
        if output.is_symlink():
            raise MigrationError("Export directory must not be a symlink")
        output.chmod(0o700)
        manifest = {
            "database": str(database),
            "table_existed": values is not None,
            "rows": len(values or {}),
            "drive_folder_id": drive_folder_id,
            "owner_email": owner_email,
        }
        if values:
            raw = _json_bytes(values)
            _write_private(output / "legacy_credentials.json", raw)
            manifest["sha256"] = hashlib.sha256(raw).hexdigest()
        _write_private(output / "migration.json", _json_bytes(manifest))
    return {
        "rows": manifest["rows"],
        "table_existed": manifest["table_existed"],
        "manifest": str(output / "migration.json"),
    }


def _verified_export(manifest, directory, backup_receipt):
    if not manifest["rows"]:
        return {}
    path = directory / "legacy_credentials.json"
    values = _private_json(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"] or len(values) != manifest["rows"]:
        raise MigrationError("Credential export changed; no database values removed")
    if not backup_receipt:
        raise MigrationError("Verified private Drive backup receipt required before removal")
    receipt = _private_json(backup_receipt)
    metadata = receipt.get("drive_metadata") or {}
    permissions = metadata.get("permissions") or []
    private_owner = (
        len(permissions) == 1
        and permissions[0].get("role") == "owner"
        and permissions[0].get("type") == "user"
        and permissions[0].get("emailAddress") == manifest["owner_email"]
    )
    if not (
        receipt.get("sha256") == manifest["sha256"]
        and metadata.get("id")
        and str(metadata.get("size")) == str(len(raw))
        and manifest["drive_folder_id"] in (metadata.get("parent_ids") or [])
        and metadata.get("shared") is False
        and private_owner
    ):
        raise MigrationError("Backup readback does not verify the private destination and exact exported file")
    return values


def _preserve_login_file(values, credential_file):
    pair = [values.get("email"), values.get("password")]
    target = Path(credential_file)
    if target.is_symlink():
        raise MigrationError("Credential destination must not be a symlink")
    if target.exists():
        with target.open(encoding="utf-8") as handle:
            current = json.load(handle)
        if not _valid_pair(current):
            raise MigrationError("Existing login file is invalid; repair it before removing database credentials")
        # A different valid account may intentionally be selected. Keep it;
        # every legacy value remains in the verified private export/backup.
        target.chmod(0o600)
        return
    if _valid_pair(pair):
        _write_private(target, _json_bytes(pair))


def remove_legacy(database, lock_file, manifest_file, backup_receipt=None, credential_file=None):
    """Drop the credential table only after verified export; checkpoint afterward.

    A checkpoint is not a claim of forensic erasure of historical file pages.
    """
    database = Path(database).resolve()
    if not database.is_file():
        raise MigrationError("Database does not exist")
    manifest_file = Path(manifest_file)
    manifest = _private_json(manifest_file)
    if str(database) != manifest["database"]:
        raise MigrationError("Export belongs to another database")
    values = _verified_export(manifest, manifest_file.parent, backup_receipt)
    with exclusive_writer(lock_file), duckdb.connect(str(database)) as conn:
        # Persist any recovered WAL indexes before DDL (DuckDB 1.5.6).
        conn.execute("CHECKPOINT")
        conn.execute("BEGIN TRANSACTION")
        try:
            current = _legacy_values(conn)
            if current is not None and current != values:
                raise MigrationError("Database credentials changed since export; export and back up again")
            if current:
                _preserve_login_file(values, credential_file or database.parent / ".brain_credentials")
            if current is not None:
                conn.execute("DROP TABLE main.credentials")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("CHECKPOINT")
    return {"credential_table_removed": True, "exported_rows": manifest["rows"]}


def sanitize_legacy(database, lock_file, manifest_file, backup_receipt=None, credential_file=None):
    """Check known credential bytes; rebuild stopped DB only when necessary."""
    database = Path(database).absolute()
    if database.is_symlink() or database.parent.resolve() != database.parent or not database.is_file():
        raise MigrationError("Database must be an existing non-symlink path")
    manifest_file = Path(manifest_file)
    manifest = _private_json(manifest_file)
    if str(database) != manifest["database"]:
        raise MigrationError("Export belongs to another database")
    values = _verified_export(manifest, manifest_file.parent, backup_receipt)
    known = [value for value in values.values() if isinstance(value, str) and value]
    private_login = Path(credential_file or database.parent / ".brain_credentials")
    if private_login.exists():
        pair = _private_json(private_login)
        if not _valid_pair(pair):
            raise MigrationError("Private login file is invalid")
        known.extend(pair)
    environment_pair = [os.environ.get("BRAIN_EMAIL"), os.environ.get("BRAIN_PASSWORD")]
    if _valid_pair(environment_pair):
        known.extend(environment_pair)
    if not known:
        raise MigrationError("No known project credential values are available for exact-byte verification")
    with exclusive_writer(lock_file):
        with duckdb.connect(str(database)) as conn:
            if _legacy_values(conn) is not None:
                raise MigrationError("Perform backup-first logical removal before physical sanitization")
            conn.execute("CHECKPOINT")
        try:
            result = compact_if_needed(database, known)
        except CompactionError as error:
            raise MigrationError(str(error), rollback_path=error.rollback_path) from None
    result["migration_complete"] = bool(result["physical_removal_verified"] and not result.get("cleanup_incomplete"))
    return result
