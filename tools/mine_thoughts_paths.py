"""Input/output paths and the small JSON loader for the thought miner.

Split out of `tools/mine_template_thoughts.py`, which re-exports these names.
"""

import json
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORUM = os.path.join(PROJECT_DIR, "docs", "forum")
OUT = os.path.join(FORUM, "template_thoughts.json")
PV_CATALOG = os.path.join(PROJECT_DIR, "data", "templates_pv_option.json")
TEMPLATES = os.path.join(FORUM, "forum_templates.json")


def _load(path):
    with open(path) as fh:
        return json.load(fh)
