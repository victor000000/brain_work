"""Store downloaded data fields and datasets.

Rows outside the project's data scope are dropped on the way in — see
`core/scope.py`. `data_fields` and `datasets` stayed clean through the last
refresh only because the downloader happened to request pv/option
subcategories; nothing enforced it. This makes the guarantee structural.
"""

import json

from core.scope import in_scope


def store_data_fields(conn, fields):
    """Insert or replace data_fields and datasets rows from API results."""
    if not fields:
        return
    frows, drows, seen = [], [], set()
    for f in fields:
        ds = f.get("dataset") or {}
        cat = f.get("category") or {}
        sub = f.get("subcategory") or {}
        if not in_scope(cat.get("id")):
            continue
        frows.append(
            (
                f.get("id", ""),
                f.get("description", ""),
                ds.get("id", ""),
                ds.get("name", ""),
                cat.get("id", ""),
                cat.get("name", ""),
                sub.get("id", ""),
                sub.get("name", ""),
                f.get("region", ""),
                f.get("delay"),
                f.get("universe", ""),
                f.get("type", ""),
                f.get("dateCoverage"),
                f.get("coverage"),
                f.get("userCount"),
                f.get("alphaCount"),
                f.get("pyramidMultiplier"),
                json.dumps(f.get("themes", [])),
                json.dumps(f),
            )
        )
        dk = (ds.get("id", ""), f.get("region", ""), f.get("delay"), f.get("universe", ""))
        if ds.get("id") and dk not in seen:
            seen.add(dk)
            drows.append(
                (
                    ds.get("id", ""),
                    ds.get("name", ""),
                    cat.get("id", ""),
                    cat.get("name", ""),
                    sub.get("id", ""),
                    sub.get("name", ""),
                    f.get("region", ""),
                    f.get("delay"),
                    f.get("universe", ""),
                )
            )
    conn.executemany("INSERT OR REPLACE INTO data_fields VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", frows)
    if drows:
        conn.executemany("INSERT OR REPLACE INTO datasets VALUES (?,?,?,?,?,?,?,?,?)", drows)
    conn.commit()
