"""Walk the mined corpus and turn expression lines into template rows.

Split out of `tools/mine_forum_templates.py`, which re-exports these names;
`main` calls them in the same order the old single function did.
"""

from collections import Counter, defaultdict

from tools.mine_forum_classify import classify, residual_tokens
from tools.mine_forum_patterns import ANY_OP_RE
from tools.mine_forum_text import iter_text, looks_like_alpha, normalize_expression_line, skeletonize


def scan_documents(bodies, comments, reference):
    """Accumulate every expression line into skeleton buckets.

    Returns (skel_posts, skel_example, skel_meta, kind_count, mention, n_docs).
    """
    skel_posts = defaultdict(set)
    skel_example = {}
    skel_meta = {}
    kind_count = Counter()
    mention = Counter()
    n_docs = 0

    for kind, pid, text in iter_text(bodies, comments):
        n_docs += 1
        for raw in text.split("\n"):
            line = raw.strip()
            if len(line) < 10 or len(line) > 400:
                continue
            line = normalize_expression_line(line)
            if not looks_like_alpha(line):
                continue
            pv, other = classify(line, reference)
            sk = skeletonize(line)
            skel_posts[sk].add(pid)
            skel_example.setdefault(sk, line)
            meta = skel_meta.setdefault(sk, {"pv": set(), "other": set(), "kinds": set()})
            meta["pv"] |= pv
            meta["other"] |= other
            meta["kinds"].add(kind)
            kind_count[kind] += 1
            for m in ANY_OP_RE.finditer(line):
                mention[m.group(1)] += 1

    return skel_posts, skel_example, skel_meta, kind_count, mention, n_docs


def build_rows(skel_posts, skel_example, skel_meta, posts):
    """One output row per skeleton, most-seen first."""
    rows = []
    for sk, pids in sorted(skel_posts.items(), key=lambda kv: -len(kv[1])):
        m = skel_meta[sk]
        m["other"] |= residual_tokens(sk)
        first = next(iter(pids))
        rows.append(
            {
                "skeleton": sk,
                "posts": len(pids),
                "example": skel_example[sk],
                "pv_option_fields": sorted(m["pv"]),
                "other_fields": sorted(m["other"]),
                "fillable_from_pv_option": not m["other"],
                "found_in": sorted(m["kinds"]),
                "topic": posts.get(first, {}).get("topic_name", ""),
                "html_url": posts.get(first, {}).get("html_url", ""),
            }
        )
    return rows
