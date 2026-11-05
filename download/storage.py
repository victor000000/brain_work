"""Store downloaded categories and data fields.

Category rows are filtered to the project's data scope on the way in. Without
that guard this function undoes the pv/option restriction every time it runs —
it re-inserted all 62 categories, 55 of them out of scope, on the refresh that
followed the cleanup.
"""

import json
import logging

from core.scope import keep_category
from download.storage_fields import store_data_fields  # noqa: F401

log = logging.getLogger("dl")


def store_categories(conn, categories):
    rows = []
    skipped = 0
    for cat in categories:
        if not keep_category(cat):
            skipped += 1
            continue
        rows.append(
            (
                cat["id"],
                cat["name"],
                None,
                cat.get("datasetCount", 0),
                cat.get("fieldCount", 0),
                cat.get("alphaCount", 0),
                cat.get("userCount", 0),
                cat.get("valueScore"),
                json.dumps(cat.get("region", [])),
                json.dumps(cat),
            )
        )
        for ch in cat.get("children", []):
            if not keep_category(ch):
                skipped += 1
                continue
            rows.append(
                (
                    ch["id"],
                    ch["name"],
                    cat["id"],
                    ch.get("datasetCount", 0),
                    ch.get("fieldCount", 0),
                    ch.get("alphaCount", 0),
                    ch.get("userCount", 0),
                    ch.get("valueScore"),
                    json.dumps(ch.get("region", [])),
                    json.dumps(ch),
                )
            )
    conn.executemany("INSERT OR REPLACE INTO dataset_categories VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    if skipped:
        log.info("Skipped %d out-of-scope category rows", skipped)
    log.info("Stored %d category rows", len(rows))
