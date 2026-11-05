"""Paths and scope reference for the cnhkmcp / learn-docs template miner.

Split out of `tools/mine_cnhkmcp_templates.py`, which re-exports these names.
Scope classification is DB-free on purpose: the miner runs while the explorer
holds brain_data.duckdb, so it uses docs/forum/field_category_reference.json
(the 65 pv/option names + 865 known-foreign names) plus the field names the
forum mining already confirmed.
"""

import json
import os
import re

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(PROJECT_DIR, "vendor", "cnhkmcp")
LEARN = os.path.join(PROJECT_DIR, "docs", "learn")
FORUM_DIR = os.path.join(PROJECT_DIR, "docs", "forum")
OUT = os.path.join(FORUM_DIR, "cnhkmcp_mined_templates.json")


def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


REF = json.loads(_read(os.path.join(FORUM_DIR, "field_category_reference.json")))
POSITIVE = {f.lower() for f in REF["pv_option_fields"]}
FORUM = json.loads(_read(os.path.join(FORUM_DIR, "forum_templates.json")))
POSITIVE |= {f.lower() for r in FORUM for f in (r.get("pv_option_fields") or [])}
EXISTING = {re.sub(r"\s+", "", r["skeleton"]) for r in FORUM}
CURATED = json.loads(_read(os.path.join(FORUM_DIR, "cnhkmcp_curated_templates.json")))
EXISTING |= {re.sub(r"\s+", "", c["expression"]) for c in CURATED}
