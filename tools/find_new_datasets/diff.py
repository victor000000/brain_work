"""Identify subcategories whose datasetCount has grown vs the local cache."""


def grew_subcats(api_subcats, cached_counts, force_all):
    """Return list of (subcat_id, name, old_count, new_count, delta) needing scan.

    A subcategory is flagged when:
      - `force_all` is True (covers stale/missing local cache), or
      - the subcategory isn't in the local cache, or
      - the new_count > old_count.
    """
    out = []
    for sub in api_subcats:
        sid = sub["id"]
        new_count = sub.get("datasetCount", 0) or 0
        old_count, _ = cached_counts.get(sid, (0, ""))
        delta = new_count - old_count
        if force_all or sid not in cached_counts or delta > 0:
            out.append((sid, sub.get("name", ""), old_count, new_count, delta))
    return out
