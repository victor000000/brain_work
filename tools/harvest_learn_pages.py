"""Fetch-or-load one learn page, so the harvest loop stays a loop.

Split out of `tools/harvest_learn_docs.py`. Returns the document, its filename
and which path produced it, so the caller prints and counts in the same order
as before the split.
"""

import json
import os

from tools.harvest_learn_client import fetch_page
from tools.harvest_learn_store import safe_name, write_json


def index_row(tutorial_id, tutorial, page, doc, fname):
    """The index.json entry for one crawled page."""
    seq = doc.get("sequence") or 0
    return {
        "tutorial": tutorial_id,
        "tutorial_category": tutorial.get("category"),
        "page_id": page.get("id"),
        "title": doc.get("title") or page.get("title"),
        "sequence": seq,
        "last_modified": doc.get("lastModified"),
        "file": fname,
    }


def one_page(session, out_dir, tutorial_id, page, force=False):
    """Return (doc, fname, state) for one page: fetched, cached or failed.

    `sequence` is absent from the /tutorials listing — it only comes back on
    the page itself, so the filename is settled after fetching.
    """
    pid = page.get("id")
    cached = sorted(f for f in os.listdir(out_dir) if f.endswith(f"_{safe_name(pid)}.json"))
    if cached and not force:
        fname = cached[0]
        with open(os.path.join(out_dir, fname)) as fh:
            return json.load(fh), fname, "cached"

    doc = fetch_page(session, pid)
    if doc is None:
        return None, "", "failed"
    doc.setdefault("tutorial", tutorial_id)
    seq = doc.get("sequence") or page.get("sequence") or 0
    fname = f"{seq:03d}_{safe_name(pid)}.json"
    write_json(os.path.join(out_dir, fname), doc)
    return doc, fname, "fetched"
