"""Export PV/options metadata from a clean DuckDB snapshot to Parquet.

Run with python -m tools.export_brain_catalog --db SNAPSHOT --output DIRECTORY.
This exports descriptions and availability, not historical market observations.
"""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from core.db import connect_for_reading

_SCOPE = "category_id IN ('pv', 'option')"
QUERIES = {
    "fields": f"""SELECT category_id || ':' || dataset_id || ':' || id AS field_key,
        category_id, dataset_id, id AS field_id,
        to_json(list_sort(list_distinct(list(description)))) AS descriptions_json,
        to_json(list_sort(list_distinct(list(type)))) AS types_json,
        to_json(list_sort(list_distinct(list(region)))) AS regions_json,
        COUNT(*) AS availability_rows
        FROM data_fields WHERE {_SCOPE} GROUP BY category_id, dataset_id, id
        ORDER BY category_id, dataset_id, id""",
    "availability": f"SELECT * FROM data_fields WHERE {_SCOPE} ORDER BY category_id,dataset_id,id,region,universe,delay",
    "datasets": f"""SELECT DISTINCT dataset_id, dataset_name, category_id,
        subcategory_id, subcategory_name FROM data_fields WHERE {_SCOPE}
        ORDER BY category_id, dataset_id, dataset_name""",
}


def export_catalog(db, output):
    """Publish a complete directory only after Parquet readback succeeds."""
    source, destination = Path(db).resolve(), Path(output).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(f"Refusing to replace existing export: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        counts = {}
        conn = connect_for_reading(source)
        try:
            for name, query in QUERIES.items():
                conn.execute(
                    f"COPY ({query}) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(stage / f"{name}.parquet")]
                )
            conn.execute(f"COPY ({QUERIES['fields']}) TO ? (FORMAT CSV, HEADER TRUE)", [str(stage / "fields.csv")])
            conn.execute(f"COPY ({QUERIES['fields']}) TO ? (FORMAT JSON, ARRAY FALSE)", [str(stage / "fields.jsonl")])
        finally:
            conn.close()
        catalog = duckdb.connect(str(stage / "catalog.duckdb"))
        try:
            for name in QUERIES:
                catalog.execute(
                    f"CREATE TABLE {name} AS SELECT * FROM read_parquet(?)", [str(stage / f"{name}.parquet")]
                )
                counts[name] = catalog.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            duplicate_keys = catalog.execute(
                "SELECT COUNT(*) FROM (SELECT field_key FROM fields GROUP BY 1 HAVING COUNT(*) > 1)"
            ).fetchone()[0]
            total_availability = catalog.execute("SELECT COALESCE(SUM(availability_rows),0) FROM fields").fetchone()[0]
            if duplicate_keys or total_availability != counts["availability"]:
                raise ValueError("Catalog keys or Parquet availability counts disagree")
            categories = dict(catalog.execute("SELECT category_id,COUNT(*) FROM fields GROUP BY 1").fetchall())
            missing_descriptions = catalog.execute(
                "SELECT COUNT(*) FROM fields WHERE descriptions_json IS NULL OR descriptions_json IN ('[]','[\"\"]')"
            ).fetchone()[0]
            catalog.execute("CHECKPOINT")
        finally:
            catalog.close()
        manifest = {
            "exported_at_utc": datetime.now(UTC).isoformat(),
            "source_snapshot": str(source),
            "source_snapshot_mtime_utc": datetime.fromtimestamp(source.stat().st_mtime, UTC).isoformat(),
            "metadata_source": "Saved original BRAIN /data-fields API responses in the DuckDB snapshot",
            "metadata_retrieved_at_utc": None,
            "freshness_note": "Export time is not retrieval time. Fresh HTTP response receipts are separate.",
            "historical_values_included": False,
            "counts": counts,
            "categories": categories,
            "fields_without_description": missing_descriptions,
            "sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.iterdir()) if p.is_file()
            },
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Temporary directories start at 0700; consumers run as other users.
        stage.chmod(0o755)
        os.rename(stage, destination)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Clean DuckDB snapshot; do not open the live writer's database")
    parser.add_argument("--output", required=True, help="New export directory")
    args = parser.parse_args()
    print(json.dumps(export_catalog(args.db, args.output), indent=2))


if __name__ == "__main__":
    main()
