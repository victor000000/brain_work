"""Decode and rebuild the orphan rows `query_orphan_rows` selects.

Split out of `runner/explore_loop/reattach.py`, which re-exports these names.
The SQL lives in `runner.explore_loop.reattach_query`; this module turns the
stored rows back into the batch dicts the poll loop knows.
"""

import calendar
import json
import time

from runner.explore_loop.reattach_query import _TS_FORMAT, query_orphan_rows  # noqa: F401

API_BASE = "https://api.worldquantbrain.com"


def _epoch(value):
    """Parse the stored 'YYYY-mm-dd HH:MM:SS UTC' timestamp; None on failure."""
    if not value:
        return None
    try:
        return calendar.timegm(time.strptime(value, _TS_FORMAT))
    except (ValueError, TypeError):
        return None


def _decode_settings(raw):
    try:
        settings = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        settings = {}
    return settings if isinstance(settings, dict) else {}


def _decode_exprs(expression):
    """Expressions are stored on the parent row as a JSON array."""
    if not expression:
        return []
    try:
        exprs = json.loads(expression)
    except (ValueError, TypeError):
        return []
    if isinstance(exprs, list):
        return [e for e in exprs if isinstance(e, str)]
    return []


def build_batches(rows, now):
    """Rebuild the batch dicts the poll loop re-attaches from stored rows."""
    batches = []
    for sim_id, batch_idx, region, universe, delay, expression, raw_settings, completed_at in rows:
        settings = _decode_settings(raw_settings)
        settings.setdefault("region", region)
        settings.setdefault("universe", universe)
        settings.setdefault("delay", delay)
        if not settings.get("region") or not settings.get("universe"):
            continue
        submitted_at = _epoch(completed_at) or now
        batches.append(
            {
                "pid": sim_id,
                "loc": f"{API_BASE}/simulations/{sim_id}",
                "exprs": _decode_exprs(expression),
                "idx": batch_idx,
                "settings": settings,
                "submitted_at": submitted_at,
                "reattached": True,
            }
        )
    return batches
