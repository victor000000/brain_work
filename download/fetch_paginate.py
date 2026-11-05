"""Pagination helpers for fetching data fields from the BRAIN API.

Both helpers report failure explicitly (`None` for the count, an incomplete
flag for the pages) so callers can refuse to mark a combo downloaded. A
truncated fetch that was recorded as done used to be skipped forever by
`--resume`.
"""

import logging

from download.session import API_BASE, PAGE_SIZE

log = logging.getLogger("dl")


def _get_field_count(brain, region, universe, delay, sid):
    """How many fields exist for a subcategory, or None when it cannot be told.

    A 200 whose body is not a dict (or carries no integer `count`) is a
    malformed response, not "zero fields" — returning 0 there permanently
    marked the combo downloaded with no fields stored.
    """
    resp = brain.get(
        f"{API_BASE}/data-fields",
        params={
            "instrumentType": "EQUITY",
            "region": region,
            "universe": universe,
            "delay": delay,
            "subcategory": sid,
            "limit": 1,
        },
    )
    if resp.status_code != 200:
        log.warning("  %s: HTTP %d, skip", sid, resp.status_code)
        return None
    try:
        data = resp.json()
    except ValueError:
        log.warning("  %s: unparseable 200 body, skip", sid)
        return None
    if not isinstance(data, dict):
        log.warning("  %s: unexpected 200 body (%s), skip", sid, type(data).__name__)
        return None
    count = data.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        log.warning("  %s: missing/invalid count (%r), skip", sid, count)
        return None
    return count


def _paginate_fields(brain, region, universe, delay, sid, count):
    """Fetch every page of fields for a subcategory.

    Returns `(fields, complete)`. `complete` is False when the walk was cut
    short — a 400 at the API limit, any other non-200, an unparseable body, or
    a page that stops before `count` rows are collected. Callers must only
    record the combo as downloaded when `complete` is True.
    """
    fields, offset = [], 0
    while offset < count:
        r = brain.get(
            f"{API_BASE}/data-fields",
            params={
                "instrumentType": "EQUITY",
                "region": region,
                "universe": universe,
                "delay": delay,
                "subcategory": sid,
                "limit": PAGE_SIZE,
                "offset": offset,
            },
        )
        if r.status_code == 400:
            log.warning("  %s: offset %d hit API limit, got %d/%d", sid, offset, len(fields), count)
            return fields, False
        if r.status_code != 200:
            log.warning("  %s: HTTP %d at offset %d, got %d/%d", sid, r.status_code, offset, len(fields), count)
            return fields, False
        try:
            page_data = r.json()
        except ValueError:
            log.warning("  %s: unparseable page at offset %d, got %d/%d", sid, offset, len(fields), count)
            return fields, False
        results = page_data.get("results", []) if isinstance(page_data, dict) else []
        if not results:
            log.warning("  %s: empty page at offset %d, got %d/%d", sid, offset, len(fields), count)
            return fields, False
        fields.extend(results)
        offset += len(results)
    return fields, len(fields) >= count
