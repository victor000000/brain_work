#!/usr/bin/env python3
"""Harvest the BRAIN learn documentation.

The rendered site at platform.worldquantbrain.com/learn/documentation is a
single-page app — its HTML is a 2 KB shell with no content. The documentation
itself comes from two API endpoints:

    GET /tutorials                    -> 11 tutorials, each with its page list
    GET /tutorial-pages/{page_id}     -> one page: title, category, content blocks

cnhkmcp ships a copy of these under `knowledge/`, but that copy stops around
2025-03; the live pages were last modified 2026-09. This fetches current ones.

Writes one JSON per page to docs/learn/, named `<sequence>_<slug>.json`, plus
an index.json. Skips pages already fetched unless --force.

Usage:
    python3 tools/harvest_learn_docs.py
    python3 tools/harvest_learn_docs.py --force
"""

import argparse
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.harvest_learn_client import authenticate, fetch_tutorials  # noqa: E402
from tools.harvest_learn_pages import index_row, one_page  # noqa: E402
from tools.harvest_learn_store import safe_name, write_json  # noqa: E402,F401

OUT_DIR = os.path.join(PROJECT_DIR, "docs", "learn")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--force", action="store_true", help="re-fetch pages already on disk")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    session = authenticate()

    tutorials = fetch_tutorials(session)
    print(f"tutorials: {len(tutorials)}")

    index, fetched, skipped, failed = [], 0, 0, 0
    for tut in tutorials:
        t_id = tut.get("id")
        pages = tut.get("pages") or []
        print(f"\n{tut.get('category', '?'):22} {t_id}  ({len(pages)} pages)")
        for page in pages:
            pid = page.get("id")
            if not pid:
                continue

            doc, fname, state = one_page(session, args.out, t_id, page, args.force)
            if state == "failed":
                failed += 1
                print(f"  ! {pid}  FAILED")
                continue
            if state == "cached":
                skipped += 1
                print(f"  = {fname}  (cached)")
            else:
                fetched += 1
                print(f"  + {fname}  ({len(doc.get('content') or [])} blocks)")

            index.append(index_row(t_id, tut, page, doc, fname))
            time.sleep(0.4)

    index.sort(key=lambda r: (r["tutorial"] or "", r["sequence"] or 0))
    write_json(os.path.join(args.out, "index.json"), index)

    print(f"\nfetched {fetched}, cached {skipped}, failed {failed}")
    print(f"index: {len(index)} pages -> {os.path.join(args.out, 'index.json')}")


if __name__ == "__main__":
    main()
