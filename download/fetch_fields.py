"""Fetch all data fields across regions, with resume support.

Only in-scope (pv/option) subcategories are fetched or logged: the downloader
walks whatever list it is handed, and `download/brain_data.py` hands it all 62
categories, which used to write out-of-scope `download_log` rows and spend API
budget on fields `storage_fields.py` then discarded.

A combo is marked downloaded only when its pagination was complete — an
interrupted fetch must be retried, not skipped by `--resume`.
"""

import logging

from core.regions import REGION_CONFIGS
from core.scope import in_scope
from download.db_schema import is_downloaded, mark_downloaded
from download.fetch_paginate import _get_field_count, _paginate_fields
from download.storage import store_data_fields

log = logging.getLogger("dl")


def _derive_region_config():
    """Group the canonical (region, universe, delay) matrix by region.

    Derived rather than restated. The two copies had already drifted — CHN's
    delays were [1, 0] in core.regions and [0, 1] here — and a silently
    duplicated matrix is a download that quietly skips or reorders combos.

    Refresh the matrix via `tools.discover_simulation_matrix`, which writes the
    canonical result that `core.regions.REGION_CONFIGS` mirrors.
    """
    config: dict = {}
    for region, universe, delay in REGION_CONFIGS:
        entry = config.setdefault(region, {"universes": [], "delays": []})
        if universe not in entry["universes"]:
            entry["universes"].append(universe)
        if delay not in entry["delays"]:
            entry["delays"].append(delay)
    return config


REGION_CONFIG = _derive_region_config()


def download_all_fields(brain, conn, subcategories):
    total, skipped = 0, 0

    for region, cfg in REGION_CONFIG.items():
        for universe in cfg["universes"]:
            for delay in cfg["delays"]:
                log.info("--- %s/%s/d%d ---", region, universe, delay)
                added, skip = _download_region_fields(brain, conn, subcategories, region, universe, delay)
                total += added
                skipped += skip

    if skipped:
        log.info("Skipped %d already-downloaded combos", skipped)
    return total


def _download_region_fields(brain, conn, subcategories, region, universe, delay):
    """Download all subcategory fields for one region/universe/delay combo."""
    added, skipped = 0, 0
    for sub in subcategories:
        sid = sub["id"]
        if not in_scope(sid):
            continue
        if is_downloaded(conn, region, universe, delay, sid):
            skipped += 1
            continue

        count = _get_field_count(brain, region, universe, delay, sid)
        if count is None:
            continue
        if count == 0:
            mark_downloaded(conn, region, universe, delay, sid, 0)
            continue

        log.info("  %s: %d fields", sid, count)
        fields, complete = _paginate_fields(brain, region, universe, delay, sid, count)
        if fields:
            # Partial rows are still worth keeping; INSERT OR REPLACE makes the
            # retry idempotent.
            store_data_fields(conn, fields)
            added += len(fields)
            log.info("    Stored %d (total: %d)", len(fields), added)
        if not complete:
            log.warning("    %s: incomplete (%d/%d) — not marking downloaded", sid, len(fields), count)
            continue
        mark_downloaded(conn, region, universe, delay, sid, len(fields))
    return added, skipped
