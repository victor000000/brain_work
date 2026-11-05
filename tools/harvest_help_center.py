#!/usr/bin/env python3
"""Harvest the BRAIN help-centre articles (read-only).

A second Zendesk corpus, separate from the community posts
`tools/spider_forum.py` walks: 602 articles in 90 sections. Nothing else in the
tree reads it, so an expression written into an article is invisible to every
corpus on disk until this runs.

The list endpoint already returns each article's rendered body, so the whole
corpus is seven requests rather than one per article.

Only `en-us` exists — `zh-cn`, `zh-tw`, `ja` and `ko` each return 0 articles,
which is what the community forum's Chinese traffic suggests (that material is
in the forum, not the help centre).

Writes docs/forum/help_center_articles.json. Checkpointed and resumable: a
re-run fetches only what is missing.

Usage:
    python3 tools/harvest_help_center.py
    python3 tools/harvest_help_center.py --out docs/forum
"""

import argparse
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from download.forum.client import ForumClient  # noqa: E402
from download.forum.spider_checkpoint import DEFAULT_OUT, load_checkpoint, save_checkpoint  # noqa: E402

LOCALES = ("en-us",)


def article_rows(client, locale):
    """Every article's metadata and body, paged.

    The client can return None for a page (a transient failure), which must not
    be checkpointed as "no more pages" — the caller keeps the previous value.
    """
    out, page = {}, 1
    while True:
        data = client.get_json(f"/api/v2/help_center/{locale}/articles?per_page=100&page={page}")
        if not isinstance(data, dict):
            print(f"  {locale} page {page}: no data")
            break
        batch = data.get("articles") or []
        if not batch:
            break
        for a in batch:
            out[str(a.get("id"))] = {
                "id": str(a.get("id")),
                "title": a.get("title"),
                "body": a.get("body"),
                "html_url": a.get("html_url"),
                "section_id": a.get("section_id"),
                "created_at": a.get("created_at"),
                "updated_at": a.get("updated_at"),
            }
        print(f"  {locale} page {page}/{data.get('page_count')}: {len(out)} articles")
        if page >= (data.get("page_count") or 1):
            break
        page += 1
        time.sleep(0.2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--locales", nargs="*", default=list(LOCALES))
    args = ap.parse_args()

    path = os.path.join(args.out, "help_center_articles.json")
    done = load_checkpoint(path)
    print(f"already stored: {len(done)}")

    client = ForumClient()
    fetched = 0
    for locale in args.locales:
        rows = article_rows(client, locale)
        for aid, row in rows.items():
            if not row.get("body") or aid not in done:
                fetched += 1
            done[aid] = row

    save_checkpoint(path, done)
    print(f"stored {len(done)} articles ({fetched} fetched/refreshed) -> {path}")


if __name__ == "__main__":
    main()
