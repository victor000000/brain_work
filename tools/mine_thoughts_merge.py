"""Fold the structured rationale that already ships locally into the thoughts.

Split out of `tools/mine_template_thoughts.py`, which re-exports
`merge_structured`.
"""

import os
import re

from tools.mine_forum_templates import skeletonize
from tools.mine_thoughts_paths import FORUM, PV_CATALOG, _load
from tools.mine_thoughts_text import MAX_THOUGHT_CHARS


def _add(thoughts: dict, skeleton: str, thought: dict) -> None:
    bucket = thoughts.setdefault(skeleton, [])
    if not any(t.get("text") == thought["text"] for t in bucket):
        bucket.append(thought)


def merge_structured(thoughts: dict, forum_dir: str = FORUM, catalog: str = PV_CATALOG) -> None:
    """Fold in the rationale that already ships as structured fields."""
    path = os.path.join(forum_dir, "cnhkmcp_curated_templates.json")
    if os.path.exists(path):
        for row in _load(path):
            if not isinstance(row, dict) or not row.get("fillable_from_pv_option"):
                continue
            expr = re.sub(r"^\s*[\w一-鿿]+\s*=\s*", "", row.get("expression") or "", count=1)
            if not expr:
                continue
            text = "\n".join(x for x in (row.get("hypothesis"), row.get("settings")) if x)
            if text:
                _add(
                    thoughts,
                    skeletonize(expr),
                    {
                        "source": "cnhkmcp_curated",
                        "name": row.get("name") or "",
                        "text": text[:MAX_THOUGHT_CHARS],
                    },
                )

    if os.path.exists(catalog):
        data = _load(catalog)
        for t in data.get("templates", []):
            expr = t.get("expression") or ""
            if not expr:
                continue
            text = " — ".join(x for x in (t.get("description"), t.get("rationale")) if x)
            if text:
                _add(
                    thoughts,
                    skeletonize(expr),
                    {
                        "source": "pv_option_catalog",
                        "name": t.get("name") or "",
                        "category": t.get("category") or "",
                        "text": text[:MAX_THOUGHT_CHARS],
                    },
                )
