"""Walk the corpus and gather the thoughts attached to each skeleton.

Split out of `tools/mine_template_thoughts.py`, which re-exports `collect` and
`_rank` (the tests import both from there).
"""

import re
from collections import defaultdict

from tools.mine_forum_templates import PY_MARKERS, looks_like_alpha, normalize_expression_line, skeletonize
from tools.mine_thoughts_text import MAX_THOUGHT_CHARS, paragraph_around

# Prose that carries a decision (settings, measured effect) ranks above a bare
# restatement of the formula.
_TELLING = re.compile(
    # `IC` as the metric, not the "ic" inside public/logic/dynamic: letters on
    # either side disqualify it, but a neighbouring CJK character does not.
    r"((?<![A-Za-z])IC(?![A-Za-z])|sharpe|夏普|fitness|turnover|换手|neutraliz|中性化|universe|region|decay|truncation"
    r"|回测|hypothesis|理由|逻辑|because|correlat|相关性|收益)",
    re.I,
)


def collect(docs, posts: dict) -> dict:
    """Thoughts keyed by skeleton from (kind, post_id, text) documents."""
    thoughts: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, set] = defaultdict(set)

    for kind, pid, text in docs:
        for raw in text.split("\n"):
            stripped = raw.strip()
            if len(stripped) < 10 or len(stripped) > 400:
                continue
            line = normalize_expression_line(stripped)
            if not looks_like_alpha(line):
                continue
            skeleton = skeletonize(line)
            block = paragraph_around(text, stripped)
            if not block or block in seen[skeleton]:
                continue
            seen[skeleton].add(block)
            post = posts.get(str(pid)) or {}
            thoughts[skeleton].append(
                {
                    "source": kind,
                    "post_id": str(pid),
                    "title": (post.get("title") or "")[:140],
                    "url": post.get("html_url") or "",
                    "created_at": post.get("created_at") or "",
                    "text": block,
                }
            )
    return thoughts


def _rank(thought: dict) -> float:
    score = min(len(thought["text"]), MAX_THOUGHT_CHARS) / MAX_THOUGHT_CHARS
    if _TELLING.search(thought["text"]):
        score += 2.0
    if PY_MARKERS.search(thought["text"]):
        # The line matched inside a code dump (`max(0, x(y))` in a Python
        # class): still the paragraph it came from, but never the best thought.
        score -= 1.5
    if thought.get("source") == "post":
        score += 0.5
    return score
