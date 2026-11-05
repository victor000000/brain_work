#!/usr/bin/env python3
"""Mine the reasoning behind mined templates, not just the expressions.

The template miner keeps the expression-shaped lines and discards the rest of
the document — but the forum's value is not only the formulas. The prose around
them says which region/universe/settings the author used, what they observed
(hit rate, correlation, sharpe before/after) and why the signal should pay.
This pass re-walks the same corpus, keeps the block that each expression line
sits in, and joins it back to the skeleton `tools/mine_forum_templates.py`
derived from that same line — using its `skeletonize`, so both agree.

Structured rationale that already exists locally is merged in too:
cnhkmcp_curated `hypothesis`/`settings`, and the `description`/`rationale` of
data/templates_pv_option.json.

The pieces live in `mine_thoughts_paths`, `mine_thoughts_text`,
`mine_thoughts_collect`, `mine_thoughts_merge` and `mine_thoughts_main`; they
are re-exported here so `from tools.mine_template_thoughts import ...` keeps
resolving for the tests.

Writes docs/forum/template_thoughts.json.

Usage:
    python3 tools/mine_template_thoughts.py
"""

import os
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.mine_thoughts_collect import _TELLING, _rank, collect  # noqa: F401
from tools.mine_thoughts_main import MAX_THOUGHTS_PER_TEMPLATE, main  # noqa: F401
from tools.mine_thoughts_merge import _add, merge_structured  # noqa: F401
from tools.mine_thoughts_paths import FORUM, OUT, PV_CATALOG, TEMPLATES, _load  # noqa: F401
from tools.mine_thoughts_text import (  # noqa: F401
    _LABEL,
    CONTEXT_LINES,
    MAX_THOUGHT_CHARS,
    paragraph_around,
)

if __name__ == "__main__":
    main()
