"""Physical cleanup exercises temporary synthetic databases exclusively."""

import hashlib
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from core import credential_compaction as compact

SECRET = "synthetic-credential-marker-never-a-real-secret"


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retain_synthetic_bytes(path):
    # An unreferenced, block-aligned tail models dirty pages without depending
    # on allocator/compressor choices. DuckDB never sees a live secret here.
    with path.open("ab") as handle:
        handle.write(SECRET.encode().ljust(262144, b"\0"))


@pytest.fixture
def business_db(tmp_path):
    path = tmp_path / "synthetic.duckdb"
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE SCHEMA business")
        conn.execute("CREATE SEQUENCE business.ids START 7 INCREMENT 3")
        conn.execute("CREATE SEQUENCE business.unused START 29 INCREMENT 2")
        conn.execute("CREATE SEQUENCE business.descending START 20 INCREMENT -2 MINVALUE -20 MAXVALUE 20")
        conn.execute("CREATE SEQUENCE business.cycling START 2 INCREMENT 2 MINVALUE 2 MAXVALUE 6 CYCLE")
        conn.execute("SELECT nextval('business.descending') FROM range(3)")
        conn.execute("SELECT nextval('business.cycling') FROM range(3)")
        conn.execute("""CREATE TABLE business.records(
            id BIGINT PRIMARY KEY DEFAULT nextval('business.ids'),
            amount DECIMAL(16,4), label VARCHAR CHECK(length(label)>0), payload BLOB,
            stamp TIMESTAMP_NS, flags BOOLEAN)""")
        conn.execute("""INSERT INTO business.records(amount,label,payload,stamp,flags) VALUES
            (12.3456, 'alpha', '\\x00\\xFF', '2025-01-01 00:00:00.123456789', true),
            (NULL, 'beta', NULL, NULL, NULL)""")
        conn.execute("CREATE INDEX label_idx ON business.records(label)")
        conn.execute("CREATE VIEW business.record_view AS SELECT id,label FROM business.records")
        conn.execute("CREATE MACRO business.plus_one(x) AS x+1")
        conn.execute("CREATE MACRO business.labels() AS TABLE SELECT label FROM business.records")
        conn.execute("COMMENT ON TABLE business.records IS 'synthetic comment'")
        conn.execute("COMMENT ON COLUMN business.records.label IS 'label comment'")
        conn.execute("CREATE TABLE empty_table(id INTEGER)")
        conn.execute("CHECKPOINT")
    retain_synthetic_bytes(path)
    return path


def test_scan_handles_unicode_boundaries_duplicates_without_reporting_values(tmp_path):
    path = tmp_path / "bytes"
    path.write_bytes(b"before" + "边界-password".encode() + b"after")
    result = compact.scan_credential_bytes(path, ["边界-password", "missing", "边界-password"], chunk_size=3)
    assert result["patterns_checked"] == 2
    assert result["patterns_found"] == 1
    assert "password" not in str(result)


@pytest.mark.parametrize("values", [[], [""], [None], SECRET])
def test_no_empty_or_ambiguous_patterns(tmp_path, values):
    with pytest.raises(compact.CompactionError):
        compact.scan_credential_bytes(tmp_path / "not-opened", values)


def test_rebuild_preserves_data_catalogue_and_actual_next_values(business_db):
    result = compact.compact_if_needed(business_db, [SECRET])
    assert result["rebuilt"] is True
    assert result["physical_removal_verified"] is True
    assert result["verified_table_count"] == 2
    assert result["business_row_count"] == 2
    assert result["sequence_count"] == 4
    assert result["rollback_path"] is None
    assert SECRET.encode() not in business_db.read_bytes()
    assert not list(business_db.parent.glob(".credential-compaction-*"))
    with duckdb.connect(str(business_db)) as conn:
        assert conn.execute(
            "SELECT nextval('business.ids'),nextval('business.unused'),"
            "nextval('business.descending'),nextval('business.cycling')"
        ).fetchone() == (13, 29, 14, 2)
        assert conn.execute("SELECT count(*) FROM business.record_view").fetchone() == (2,)
        assert conn.execute("SELECT business.plus_one(41)").fetchone() == (42,)
        assert conn.execute("SELECT * FROM business.labels() ORDER BY label").fetchall() == [("alpha",), ("beta",)]
        conn.execute("INSERT INTO business.records(label) VALUES ('gamma')")
        assert conn.execute("SELECT id FROM business.records WHERE label='gamma'").fetchone() == (16,)
    assert business_db.stat().st_mode & 0o777 == 0o600


def test_matching_business_value_blocks_swap_and_keeps_original(tmp_path):
    path = tmp_path / "synthetic.duckdb"
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE TABLE business(value VARCHAR)")
        conn.execute("INSERT INTO business VALUES (?)", [SECRET])
    before = file_hash(path)
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(path, [SECRET])
    assert file_hash(path) == before
    assert not list(tmp_path.glob(".credential-compaction-*"))


def test_absent_byte_patterns_skip_rebuild(tmp_path):
    path = tmp_path / "clean.duckdb"
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE TABLE business(id INTEGER)")
    before = file_hash(path)
    result = compact.compact_if_needed(path, [SECRET])
    assert result["rebuilt"] is False
    assert result["physical_removal_verified"] is True
    assert result["scan_scope"] == "exact_utf8_bytes"
    assert file_hash(path) == before


def test_credential_table_must_be_dropped_even_if_no_patterns_match(tmp_path):
    path = tmp_path / "credentials.duckdb"
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE TABLE credentials(key VARCHAR,value VARCHAR)")
    before = file_hash(path)
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(path, [SECRET])
    assert file_hash(path) == before


def test_candidate_table_mismatch_never_changes_source(business_db, monkeypatch):
    before = file_hash(business_db)
    original = compact._table_hashes

    def bad_candidate(conn, database, tables):
        result = original(conn, database, tables)
        return {} if database == "candidate_db" else result

    monkeypatch.setattr(compact, "_table_hashes", bad_candidate)
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(business_db, [SECRET])
    assert file_hash(business_db) == before


def test_catalogue_mismatch_never_changes_source(business_db, monkeypatch):
    before = file_hash(business_db)
    original = compact._snapshot

    def bad_candidate(conn, database):
        catalogue, hashes = original(conn, database)
        if database == "candidate_db":
            catalogue = dict(catalogue, sequences=[])
        return catalogue, hashes

    monkeypatch.setattr(compact, "_snapshot", bad_candidate)
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(business_db, [SECRET])
    assert file_hash(business_db) == before


def test_low_space_blocks_candidate_creation(business_db, monkeypatch):
    before = file_hash(business_db)
    monkeypatch.setattr(compact.shutil, "disk_usage", lambda _: type("Usage", (), {"free": 0})())
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(business_db, [SECRET])
    assert file_hash(business_db) == before
    assert not list(business_db.parent.glob(".credential-compaction-*"))


def test_wal_refuses_before_duckdb_connection(business_db, monkeypatch):
    Path(str(business_db) + ".wal").write_bytes(b"synthetic")
    monkeypatch.setattr(compact, "_connect", lambda: pytest.fail("must not open database with WAL"))
    with pytest.raises(compact.CompactionError, match="WAL"):
        compact.compact_if_needed(business_db, [SECRET])


@pytest.mark.parametrize("ddl", ["CREATE TYPE mood AS ENUM ('happy','sad')", "CREATE TABLE complex(values INTEGER[])"])
def test_unsupported_objects_fail_closed(business_db, ddl):
    with duckdb.connect(str(business_db)) as conn:
        conn.execute(ddl)
    retain_synthetic_bytes(business_db)
    before = file_hash(business_db)
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(business_db, [SECRET])
    assert file_hash(business_db) == before


def test_source_sequence_is_never_advanced_on_success_or_failure(business_db):
    captured = []
    original = compact._connect

    class RecordingConnection:
        def __init__(self):
            self.conn = original()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.conn.close()

        def execute(self, sql, *args):
            captured.append(sql)
            return self.conn.execute(sql, *args)

    with patch.object(compact, "_connect", RecordingConnection):
        compact.compact_if_needed(business_db, [SECRET])
    assert not any("nextval(" in query.lower() for query in captured)


def test_post_swap_failure_restores_dirty_original(business_db, monkeypatch):
    before = file_hash(business_db)
    real_digest = compact._digest
    original_inode = business_db.stat().st_ino

    def installed_mismatch(path):
        if Path(path) == business_db and business_db.stat().st_ino != original_inode:
            return "incorrect-digest"
        return real_digest(path)

    monkeypatch.setattr(compact, "_digest", installed_mismatch)
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(business_db, [SECRET])
    assert file_hash(business_db) == before
    assert not list(business_db.parent.glob(".credential-compaction-*"))


def test_dirty_rollback_unlink_failure_is_reported_incomplete(business_db, monkeypatch):
    real_unlink = Path.unlink

    def refuse_rollback(self, *args, **kwargs):
        if self.name == "dirty-original.duckdb":
            raise OSError("synthetic unlink failure")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", refuse_rollback)
    result = compact.compact_if_needed(business_db, [SECRET])
    assert result["rebuilt"] is True
    assert result["physical_removal_verified"] is False
    assert result["rollback_path"]
    assert Path(result["rollback_path"]).exists()
    assert SECRET.encode() in Path(result["rollback_path"]).read_bytes()
    assert SECRET not in str(result)


@pytest.mark.parametrize(
    "relation", ['TABLE "Credentials"(key VARCHAR,value VARCHAR)', 'VIEW "Credentials" AS SELECT 1 AS value']
)
def test_mixed_case_credential_relations_are_rejected(tmp_path, relation):
    path = tmp_path / "mixed.duckdb"
    with duckdb.connect(str(path)) as conn:
        conn.execute("CREATE " + relation)
    with pytest.raises(compact.CompactionError, match="Credential table"):
        compact.compact_if_needed(path, [SECRET])


def test_exhausted_sequence_cannot_be_silently_reset(business_db):
    with duckdb.connect(str(business_db)) as conn:
        conn.execute("CREATE SEQUENCE exhausted START 1 MAXVALUE 2")
        conn.execute("SELECT nextval('exhausted') FROM range(2)")
    retain_synthetic_bytes(business_db)
    # The engine COPY preserves exhaustion; it must never restart at one.
    result = compact.compact_if_needed(business_db, [SECRET])
    assert result["physical_removal_verified"]
    with duckdb.connect(str(business_db)) as conn, pytest.raises(duckdb.SequenceException):
        conn.execute("SELECT nextval('exhausted')")


def test_swap_never_occurs_while_an_engine_connection_is_open(business_db, monkeypatch):
    original_connect = compact._connect
    original_replace = compact.os.replace
    active = []

    class TrackingConnection:
        def __init__(self):
            self.connection = original_connect()

        def __enter__(self):
            active.append(self)
            return self.connection

        def __exit__(self, *args):
            self.connection.close()
            active.remove(self)

    def replace_only_closed(*args):
        assert active == []
        return original_replace(*args)

    monkeypatch.setattr(compact, "_connect", TrackingConnection)
    monkeypatch.setattr(compact.os, "replace", replace_only_closed)
    assert compact.compact_if_needed(business_db, [SECRET])["physical_removal_verified"]


def test_failure_after_hardlink_before_swap_removes_extra_dirty_path(business_db, monkeypatch):
    before = file_hash(business_db)
    monkeypatch.setattr(compact.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("synthetic")))
    with pytest.raises(compact.CompactionError):
        compact.compact_if_needed(business_db, [SECRET])
    assert file_hash(business_db) == before
    assert business_db.stat().st_nlink == 1
    assert not list(business_db.parent.glob(".credential-compaction-*"))


def test_secret_values_are_never_in_engine_error_message(business_db, monkeypatch):
    def failing_snapshot(*_):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(compact, "_snapshot", failing_snapshot)
    with pytest.raises(compact.CompactionError) as captured:
        compact.compact_if_needed(business_db, [SECRET])
    assert SECRET not in str(captured.value)
    assert captured.value.__suppress_context__
