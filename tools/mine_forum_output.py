"""Write and report the mined forum templates.

Split out of `tools/mine_forum_templates.py`, which re-exports these names and
the paths.
"""

import json
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORUM = os.path.join(PROJECT_DIR, "docs", "forum")
OUT = os.path.join(FORUM, "forum_templates.json")


def write_rows(rows):
    # Written through a temp file and moved into place: the explorer re-reads
    # this corpus as soon as its stamp changes, so a truncate-in-place write
    # would hand a live run a half-written array to parse.
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)


def report(rows, n_docs, kind_count, mention):
    fillable = [r for r in rows if r["fillable_from_pv_option"]]
    print(f"documents scanned        : {n_docs:,} (posts + comments)")
    print(f"  expressions in posts   : {kind_count['post']:,}")
    print(f"  expressions in comments: {kind_count['comment']:,}")
    print(f"distinct templates       : {len(rows):,}")
    print(f"  fillable from pv/option: {len(fillable):,}")
    print(f"  found in comments only : {sum(1 for r in rows if r['found_in'] == ['comment']):,}")
    print(f"top operators: {mention.most_common(10)}")
    print()
    print("=== top pv/option-fillable templates ===")
    for r in sorted(fillable, key=lambda r: -r["posts"])[:20]:
        print(f"  [{r['posts']:3}p] {r['example'][:96]}")
