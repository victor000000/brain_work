#!/usr/bin/env python3
"""What the community said about a shape: the forum rationale behind a template.

`tools/mine_template_thoughts.py` walks the same corpus as the template miner
and keeps the block each expression sits in — the author's reasoning, the
settings they used, what they measured. It writes
`docs/forum/template_thoughts.json`, and until this tool nothing read it: 9,784
skeletons of rationale, write-only since 2026-10-05.

That is backwards, because the corpus already holds the evidence for shapes the
pool cannot yet reach. The clearest case so far is the `tail(...)` shape
registered on 2026-10-12: the post behind it reports prod correlation falling
from 0.77 to 0.68 — across the 0.7 submission limit — and that measurement is
the whole reason the template exists.

Reading it should not mean opening an 11 MB JSON by hand:

    python3 tools/explain_template.py 'tail('
    python3 tools/explain_template.py ts_count_nans --limit 3 --chars 400

Matching is a substring test against the skeleton and against the thought text,
so both an operator name and a phrase from a post work.
"""

import argparse
import json
import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

THOUGHTS_PATH = os.path.join(PROJECT_DIR, "docs", "forum", "template_thoughts.json")

_WS = re.compile(r"\s+")


def load_corpus(path=THOUGHTS_PATH):
    """`{skeleton: {"thoughts": [...]}}` from the thoughts file."""
    with open(path) as fh:
        data = json.load(fh)
    return data.get("templates", data)


def match_rows(corpus, query, limit=None):
    """Rows whose skeleton or attached text contains `query` (case-folded)."""
    needle = query.lower()
    out = []
    for skeleton, body in corpus.items():
        thoughts = (body or {}).get("thoughts", []) if isinstance(body, dict) else []
        if needle in skeleton.lower() or any(needle in json.dumps(t, ensure_ascii=False).lower() for t in thoughts):
            out.append((skeleton, thoughts))
            if limit is not None and len(out) >= limit:
                break
    return out


def excerpt(text, chars):
    """One-line, whitespace-collapsed heading of `text`."""
    flat = _WS.sub(" ", (text or "").strip())
    return flat if len(flat) <= chars else flat[:chars].rstrip() + "…"


def format_row(skeleton, thoughts, chars=240, per_row=2):
    """Printable block for one matched skeleton."""
    lines = [f"=== {skeleton}"]
    if not thoughts:
        lines.append("    (no attached thoughts)")
    for t in thoughts[:per_row]:
        where = t.get("title") or t.get("source") or "?"
        lines.append(f"    [{t.get('source', '?')}] {excerpt(where, 110)}")
        if t.get("created_at"):
            lines.append(f"      {t['created_at'][:10]}  {t.get('url', '')}")
        lines.append(f"      {excerpt(t.get('text', ''), chars)}")
    if len(thoughts) > per_row:
        lines.append(f"    … {len(thoughts) - per_row} more thought(s)")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("query", help="substring of a skeleton or of the forum text")
    ap.add_argument("--limit", type=int, default=5, help="max skeletons to print (0 = no limit)")
    ap.add_argument("--thoughts", type=int, default=2, help="thoughts to print per skeleton")
    ap.add_argument("--chars", type=int, default=240, help="excerpt length per thought")
    ap.add_argument("--path", default=THOUGHTS_PATH)
    args = ap.parse_args()

    corpus = load_corpus(args.path)
    rows = match_rows(corpus, args.query, limit=args.limit or None)
    if not rows:
        print(f"no skeleton or thought mentions {args.query!r} in {args.path}")
        return 1
    for skeleton, thoughts in rows:
        print(format_row(skeleton, thoughts, chars=args.chars, per_row=args.thoughts))
        print()
    print(f"{len(rows)} skeleton(s) shown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
