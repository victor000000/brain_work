#!/usr/bin/env python3
"""Mine alpha-expression templates from the help-centre articles.

The forum miner (`tools/mine_forum_templates.py`) walks community posts and
comments. The help centre is a separate Zendesk corpus, harvested by
`tools/harvest_help_center.py`, and this runs the *same* line filters over it —
`tools.mine_forum_text.looks_like_alpha` / `strip_comments` / `skeletonize` and
`tools.mine_forum_classify.classify` — so its rows are comparable with the
forum corpus' and carry the same contract: `skeleton`, `example`,
`pv_option_fields`, `other_fields`, `fillable_from_pv_option`, `found_in`.

The yield is small and the file says so: 602 articles carry 59 expression
lines, 55 distinct skeletons, 11 fillable from pv/option. The point is not
volume — it is that one shape (`rank({f}) + rank({f})`, from
`rank(close) + rank(volume)`) enters the loaded pool, where the forum's copy of
the same skeleton is flagged out because a *different* line that produced it
used `book_to_price`/`earnings_yield`.

Writes docs/forum/help_center_templates.json.

Usage:
    python3 tools/mine_help_center_templates.py [--db PATH] [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.mine_forum_classify import classify, load_reference, residual_tokens  # noqa: E402
from tools.mine_forum_text import html_to_text, looks_like_alpha, skeletonize, strip_comments  # noqa: E402

FORUM = os.path.join(PROJECT_DIR, "docs", "forum")
IN = os.path.join(FORUM, "help_center_articles.json")
OUT = os.path.join(FORUM, "help_center_templates.json")

# `alpha = ...`, in both languages — the same strip the forum miner does.
_LABEL = re.compile(r"^(alpha|expression|expr|表达式|信号|signal)\s*[:：=]\s*", re.I)  # noqa: RUF001


def scan_articles(articles, reference):
    """Accumulate every expression line into skeleton buckets."""
    skel_articles = defaultdict(set)
    skel_example = {}
    skel_meta = {}
    n_lines = 0

    for aid, art in articles.items():
        text = html_to_text(art.get("body"))
        if not text:
            continue
        for raw in text.split("\n"):
            line = _LABEL.sub("", raw.strip())
            if len(line) < 10 or len(line) > 400:
                continue
            line = strip_comments(line).rstrip(";").strip()
            if not looks_like_alpha(line):
                continue
            n_lines += 1
            pv, other = classify(line, reference)
            sk = skeletonize(line)
            skel_articles[sk].add(aid)
            skel_example.setdefault(sk, line)
            meta = skel_meta.setdefault(sk, {"pv": set(), "other": set()})
            meta["pv"] |= pv
            meta["other"] |= other

    return skel_articles, skel_example, skel_meta, n_lines


def build_rows(skel_articles, skel_example, skel_meta, articles):
    """One output row per skeleton, most-seen first — the forum corpus' shape."""
    rows = []
    for sk, aids in sorted(skel_articles.items(), key=lambda kv: -len(kv[1])):
        meta = skel_meta[sk]
        # Labels and short variables survive slotting; they cannot be filled.
        meta["other"] |= residual_tokens(sk)
        first = next(iter(aids))
        art = articles.get(first) or {}
        rows.append(
            {
                "skeleton": sk,
                "posts": len(aids),
                "example": skel_example[sk],
                "pv_option_fields": sorted(meta["pv"]),
                "other_fields": sorted(meta["other"]),
                "fillable_from_pv_option": not meta["other"],
                "found_in": ["help_center"],
                "topic": art.get("title") or "",
                "html_url": art.get("html_url") or "",
            }
        )
    return rows


def main(db_path=None, dry_run=False):
    with open(IN) as fh:
        articles = json.load(fh)
    reference = load_reference(db_path)

    skel_articles, skel_example, skel_meta, n_lines = scan_articles(articles, reference)
    rows = build_rows(skel_articles, skel_example, skel_meta, articles)
    fillable = [r for r in rows if r["fillable_from_pv_option"]]

    print(f"articles scanned         : {len(articles)}")
    print(f"expression lines         : {n_lines}")
    print(f"distinct skeletons       : {len(rows)}")
    print(f"  fillable from pv/option: {len(fillable)}")
    print(f"  rejected (foreign data): {len(rows) - len(fillable)}")
    for r in sorted(fillable, key=lambda r: -r["posts"])[:10]:
        print(f"  [{r['posts']}p] {r['example'][:88]}")

    if dry_run:
        return
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"\nwrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Mine alpha-expression templates from the help-centre articles.")
    ap.add_argument(
        "--db",
        default=None,
        help="DuckDB file holding the pv/option field reference (default: the live "
        "brain_data.duckdb). Point it at a backup to mine while the explorer holds the lock.",
    )
    ap.add_argument("--dry-run", action="store_true", help="report without writing the corpus file")
    args = ap.parse_args()
    main(args.db, args.dry_run)
