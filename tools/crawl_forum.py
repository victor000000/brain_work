#!/usr/bin/env python3
"""CLI for the forum spider: refresh the index, then bodies and comments.

`download/forum/spider.py` is a checkpointed library with no entry point; this
runs its three stages in order so a scheduled job (or the loop) can refresh the
corpus without a bespoke `python -c` invocation. All stages resume from their
checkpoints and re-queue empty entries, so repeat runs fetch only what is
missing. Read-only against the forum; credentials come from
`.brain_credentials`, not the database, so this can run while the explorer
holds the DuckDB lock.

Usage:
    python3 tools/crawl_forum.py
"""

import os
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from download.forum.spider import harvest_bodies, harvest_comments, harvest_index


def main():
    posts = harvest_index()
    ids = [p["id"] for p in posts]
    harvest_bodies(ids)
    harvest_comments(ids)
    print("forum crawl complete")


if __name__ == "__main__":
    main()
