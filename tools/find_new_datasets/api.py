"""BRAIN API helpers for the find_new_datasets tool."""

import sys

from core.scope import keep_category
from download.session import API_BASE
from tools.find_new_datasets._log import log


def fetch_subcategories(brain):
    """Return the in-scope subcategory dicts under /data-categories.

    Out-of-scope children (fundamental, model, news, ...) are dropped here:
    the tool must not report their datasets as "new" — the project cannot
    generate on them.
    """
    resp = brain.get(f"{API_BASE}/data-categories")
    if resp.status_code != 200:
        log.error("data-categories failed: HTTP %d", resp.status_code)
        sys.exit(1)
    cats = resp.json()
    all_children = [ch for cat in cats for ch in cat.get("children", [])]
    kept = [ch for ch in all_children if keep_category(ch)]
    if len(kept) != len(all_children):
        log.info("Scope filter: %d of %d subcategories in scope", len(kept), len(all_children))
    return kept
