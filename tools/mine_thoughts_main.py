"""The thought-mining pipeline, from corpus files to the coverage report.

Split out of `tools/mine_template_thoughts.py`, which re-exports `main`.
"""

import json
import os
from collections import Counter

from tools.mine_forum_templates import iter_text
from tools.mine_thoughts_collect import _rank, collect
from tools.mine_thoughts_merge import merge_structured
from tools.mine_thoughts_paths import FORUM, OUT, TEMPLATES, _load

MAX_THOUGHTS_PER_TEMPLATE = 3


def main():
    bodies = _load(os.path.join(FORUM, "forum_bodies.json"))
    comments = _load(os.path.join(FORUM, "forum_comments.json"))
    # Keyed on the *string* post id: `iter_text` yields the bodies/comments
    # keys (strings), and `collect` joins on `str(pid)`.
    posts = {str(p["id"]): p for p in _load(os.path.join(FORUM, "forum_posts.json"))}

    thoughts = collect(iter_text(bodies, comments), posts)
    merge_structured(thoughts)

    trimmed = {}
    for skeleton, bucket in thoughts.items():
        bucket.sort(key=_rank, reverse=True)
        trimmed[skeleton] = {"thoughts": bucket[:MAX_THOUGHTS_PER_TEMPLATE]}

    rows = _load(TEMPLATES)
    known = {r["skeleton"] for r in rows if isinstance(r, dict) and r.get("skeleton")}
    fillable = {
        r["skeleton"] for r in rows if isinstance(r, dict) and r.get("skeleton") and r.get("fillable_from_pv_option")
    }
    with_thoughts = set(trimmed)
    coverage = {
        "templates": len(known),
        "with_thoughts": len(with_thoughts & known),
        "fillable": len(fillable),
        "fillable_with_thoughts": len(with_thoughts & fillable),
        "thoughts_by_source": dict(Counter(t["source"] for v in trimmed.values() for t in v["thoughts"])),
    }
    with open(OUT, "w") as fh:
        json.dump({"templates": trimmed, "coverage": coverage}, fh, ensure_ascii=False, indent=1)

    print(f"templates               : {coverage['templates']:,}")
    print(f"  with thoughts         : {coverage['with_thoughts']:,}")
    print(f"  fillable pv/option    : {coverage['fillable']:,}")
    print(f"  fillable with thoughts: {coverage['fillable_with_thoughts']:,}")
    print(f"thoughts by source      : {coverage['thoughts_by_source']}")
    print(f"wrote {OUT}")
