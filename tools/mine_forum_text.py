"""Turn harvested forum text into expression-shaped, skeletonised lines.

Split out of `tools/mine_forum_templates.py`, which re-exports these names —
`tools/mine_template_thoughts.py` imports them so both miners derive identical
skeletons from identical text.
"""

import html
import re

from tools.mine_forum_candidate import QUOTED, is_named_argument
from tools.mine_forum_candidate import looks_like_alpha as looks_like_alpha
from tools.mine_forum_candidate import normalize_expression_line as normalize_expression_line
from tools.mine_forum_candidate import strip_comments as strip_comments
from tools.mine_forum_patterns import NON_FIELD


def html_to_text(body):
    if not body:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def balanced(s):
    return s.count("(") == s.count(")") and s.count("(") > 0


def iter_text(bodies, comments):
    """Yield (kind, post_id, text) for every post body and comment."""
    for pid, body in bodies.items():
        text = html_to_text(body)
        if text:
            yield "post", pid, text
    for pid, items in comments.items():
        for c in items:
            text = html_to_text(c.get("body"))
            if text:
                yield "comment", pid, text


def skeletonize(line):
    """Replace every field-like identifier in `line` with a `{f}` slot.

    Operator names, named-argument keys, quoted literals and groups survive; everything
    else — a datafield, a label, a stray variable — becomes a slot. Shared with
    the thought miner so both derive identical skeletons from identical text.
    """
    pattern = re.compile(QUOTED.pattern + r"|\b[a-z][a-z0-9_]{1,}\b|\s+", re.I)

    def replace(match):
        token = match.group(0)
        if token.startswith(('"', "'")):
            return token
        if token.isspace():
            return ""
        if (
            token.lower() in NON_FIELD
            or re.match(r"\s*\(", line[match.end() :])
            or is_named_argument(line, match.start(), match.end())
        ):
            return token
        return "{f}"

    return pattern.sub(replace, line)
