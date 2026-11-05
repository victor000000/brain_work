"""HTML → plain text for the harvested post bodies and comments.

Split out of `download/forum/spider.py`, which re-exports `html_to_text`.
"""

from __future__ import annotations

import html
import re


def html_to_text(body: str | None) -> str:
    """Strip HTML to plain text, preserving line structure."""
    if not body:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)
