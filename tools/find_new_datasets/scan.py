"""Scan /data-fields per (region, universe, delay, subcategory) for new datasets.

Walks every page of each combo (the old version sent no `offset`, so it only
ever saw page 1 and missed datasets that sort later), and ignores rows outside
the pv/option scope.
"""

from core.scope import in_scope
from download.fetch_fields import REGION_CONFIG
from download.session import API_BASE
from tools.find_new_datasets._config import MAX_PAGES, PAGE_LIMIT


def _record(results, sid, region, universe, delay, known_ids, found):
    """Add in-scope, not-yet-known datasets from one page to `found`."""
    for f in results:
        if not in_scope((f.get("category") or {}).get("id")):
            continue
        ds = f.get("dataset") or {}
        did = ds.get("id") or ""
        if not did or did in known_ids:
            continue
        entry = found.setdefault(
            did,
            {"name": ds.get("name", ""), "subcategory": sid, "seen": []},
        )
        entry["seen"].append((region, universe, delay))


def scan_subcat_for_new(brain, sid, known_ids, found):
    """Mutates `found`: dataset_id -> {'name', 'subcategory', 'seen': [(r,u,d)]}.

    Returns the count of API calls made (one per page of each region/universe/
    delay tuple).
    """
    calls = 0
    for region, cfg in REGION_CONFIG.items():
        for universe in cfg["universes"]:
            for delay in cfg["delays"]:
                offset, page = 0, 0
                while page < MAX_PAGES:
                    resp = brain.get(
                        f"{API_BASE}/data-fields",
                        params={
                            "instrumentType": "EQUITY",
                            "region": region,
                            "universe": universe,
                            "delay": delay,
                            "subcategory": sid,
                            "limit": PAGE_LIMIT,
                            "offset": offset,
                        },
                    )
                    calls += 1
                    page += 1
                    if resp.status_code != 200:
                        break
                    try:
                        data = resp.json() or {}
                    except ValueError:
                        break
                    if not isinstance(data, dict):
                        break
                    results = data.get("results") or []
                    _record(results, sid, region, universe, delay, known_ids, found)

                    offset += len(results)
                    total = data.get("count")
                    if not results or not isinstance(total, int) or offset >= total:
                        break
    return calls
