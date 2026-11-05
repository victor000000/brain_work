"""Vocabulary and regexes shared by the cnhkmcp template parser.

Split out of `tools/parse_cnhkmcp_templates.py`, which re-exports these names.
"""

import os
import re

# Known foreign fields recovered from the pre-prune classification. Needed
# because fields like `debt`, `assets` and `news_session_range` carry no
# dataset prefix, so neither DB membership nor prefix matching can place them.
REFERENCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "forum", "field_category_reference.json"
)
PREFIX_RE = re.compile(r"^([a-z]{2,8}\d+)_")

# operator / settings words that are not datafields
NOISE = {
    "region",
    "universe",
    "delay",
    "decay",
    "neutralization",
    "truncation",
    "pasteurization",
    "usa",
    "eur",
    "chn",
    "hkg",
    "glb",
    "asi",
    "kor",
    "ind",
    "mea",
    "jpn",
    "top3000",
    "top2000",
    "top1000",
    "top500",
    "top2500",
    "top800",
    "topdiv3000",
    "industry",
    "sector",
    "subindustry",
    "market",
    "std",
    "range",
    "rettype",
    "lag",
    "dense",
    "nan",
    "true",
    "false",
    "on",
    "off",
    "skip_period",
    "lookback_period",
    "window",
    "group",
    "smoothing",
    "threshold",
    "min",
}

# `<window>`, `<factor_1/>`, `<field>`: an unfilled placeholder is not a field
# and makes the template unusable as-is. Missing this marked 14 of 18 curated
# entries fillable while their expressions still carried open slots.
PLACEHOLDER_RE = re.compile(r"<[^<>]*>|/>")
TOKEN_RE = re.compile(r"\b([a-z][a-z0-9_]*)\b", re.I)
CALL_RE = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(", re.I)
