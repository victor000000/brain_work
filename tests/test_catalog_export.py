"""Catalog exchange must preserve definitions, scope and availability."""

import json

import duckdb
import pytest

from core.db import DB_PATH, OperationalError, connect, connect_for_reading
from tools.export_brain_catalog import export_catalog


def _source(tmp_path):
    path = tmp_path / "source.duckdb"
    conn = duckdb.connect(str(path))
    conn.execute("""CREATE TABLE data_fields (
        id TEXT, description TEXT, dataset_id TEXT, dataset_name TEXT,
        category_id TEXT, subcategory_id TEXT, subcategory_name TEXT,
        region TEXT, universe TEXT, delay INTEGER, type TEXT)""")
    rows = [
        ("close", "Daily close", "pv1", "Prices", "pv", "pv-price-volume", "PV", "USA", "TOP3000", 1, "MATRIX"),
        ("close", "Closing price", "pv1", "Prices", "pv", "pv-price-volume", "PV", "EUR", "TOP2500", 0, "MATRIX"),
        ("iv", "Call IV", "option1", "Options", "option", "option-option", "Option", "USA", "TOP3000", 1, "VECTOR"),
        ("sales", "Revenue", "fund1", "Fundamentals", "fundamental", "fund", "Fund", "USA", "TOP3000", 1, "MATRIX"),
    ]
    conn.executemany("INSERT INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.close()
    return path


def test_parquet_and_duckdb_preserve_all_definitions_and_cells(tmp_path):
    source = _source(tmp_path)
    output = tmp_path / "catalog"
    report = export_catalog(source, output)
    assert output.stat().st_mode & 0o005 == 0o005
    assert report["counts"] == {"fields": 2, "availability": 3, "datasets": 2}
    assert report["historical_values_included"] is False
    assert report["metadata_retrieved_at_utc"] is None
    conn = duckdb.connect(str(output / "catalog.duckdb"), read_only=True)
    try:
        descriptions = conn.execute("SELECT descriptions_json FROM fields WHERE field_id='close'").fetchone()[0]
        assert json.loads(descriptions) == ["Closing price", "Daily close"]
        assert conn.execute("SELECT types_json FROM fields WHERE field_id='iv'").fetchone()[0] == '["VECTOR"]'
        assert conn.execute("SELECT COUNT(*) FROM availability WHERE category_id='fundamental'").fetchone()[0] == 0
        assert (
            conn.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(output / "availability.parquet")]).fetchone()[0]
            == 3
        )
    finally:
        conn.close()
    assert len((output / "fields.jsonl").read_text().splitlines()) == 2
    assert (output / "fields.csv").is_file()


def test_export_failure_does_not_publish_partial_catalog(tmp_path):
    path = tmp_path / "invalid.duckdb"
    duckdb.connect(str(path)).close()
    output = tmp_path / "catalog"
    with pytest.raises(OperationalError):
        export_catalog(path, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".catalog-*"))


def test_existing_export_is_never_overwritten(tmp_path):
    source = _source(tmp_path)
    output = tmp_path / "catalog"
    output.mkdir()
    (output / "keep").write_text("existing data")
    with pytest.raises(FileExistsError):
        export_catalog(source, output)
    assert (output / "keep").read_text() == "existing data"


def test_legacy_database_entry_points_are_rejected_without_creation(tmp_path):
    with pytest.raises(OperationalError, match="Only DuckDB"):
        connect(f"file:{tmp_path / 'legacy.duckdb'}?mode=ro", uri=True)
    assert not (tmp_path / "legacy.duckdb").exists()
    for filename in ("brain_data.db", "old.sqlite", "old.sqlite3"):
        path = tmp_path / filename
        with pytest.raises(OperationalError, match="Only DuckDB"):
            connect(path)
        assert not path.exists()
    path = tmp_path / "disguised.duckdb"
    original = b"SQLite format 3\x00" + b"legacy bytes"
    path.write_bytes(original)
    with pytest.raises(OperationalError, match="SQLite databases are not supported"):
        connect_for_reading(path)
    assert path.read_bytes() == original


def test_maintenance_tools_share_the_canonical_duckdb_path():
    from tools.apply_discovery_and_redownload import _config as discovery
    from tools.find_new_datasets import _config as fields
    from tools.pyramid_status import _config as pyramid

    assert discovery.DB_PATH == fields.DB_PATH == pyramid.DB_PATH == DB_PATH
