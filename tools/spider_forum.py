#!/usr/bin/env python3
"""Spider the BRAIN community forum (read-only).

Three stages, each checkpointed independently:
    --index     topics + post metadata
    --bodies    HTML body of each post
    --comments  comments on each post

Comment volume dominates the forum: ~91k comments against 8.2k posts, so
bodies alone cover roughly a tenth of the text.

Usage:
    python3 tools/spider_forum.py --index
    python3 tools/spider_forum.py --comments
    python3 tools/spider_forum.py --all
"""

import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from download.forum.spider import DEFAULT_OUT, harvest_bodies, harvest_comments, harvest_index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", action="store_true", help="refresh topics + post metadata")
    ap.add_argument("--bodies", action="store_true", help="fetch post HTML bodies")
    ap.add_argument("--comments", action="store_true", help="fetch comments per post")
    ap.add_argument("--all", action="store_true", help="all three stages")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--no-repair",
        action="store_true",
        help="do not re-fetch checkpointed empty bodies/comments (default: repair them)",
    )
    args = ap.parse_args()

    if not any([args.index, args.bodies, args.comments, args.all]):
        ap.print_help()
        return

    t0 = time.time()
    out = args.out

    if args.index or args.all:
        print("=== index ===")
        harvest_index(out_dir=out)

    post_ids = None
    if args.bodies or args.comments or args.all:
        index_path = os.path.join(out, "forum_posts.json")
        if not os.path.exists(index_path):
            print("no post index — run --index first")
            sys.exit(1)
        with open(index_path) as fh:
            posts = json.load(fh)
        post_ids = [p["id"] for p in posts]
        print(f"loaded {len(post_ids)} post ids")

    if args.bodies or args.all:
        print("\n=== bodies ===")
        harvest_bodies(post_ids, out_dir=out, workers=args.workers, repair_empty=not args.no_repair)

    if args.comments or args.all:
        print("\n=== comments ===")
        harvest_comments(post_ids, out_dir=out, workers=args.workers, repair_empty=not args.no_repair)

    print(f"\ntotal {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
