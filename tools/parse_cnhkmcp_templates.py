"""Parse both template formats in cnhkmcp's curated collection, then classify
each by whether it can be filled from pv/option data alone.

The source file lives inside the cnhkmcp package, which is not part of this
repo — unzip the wheel and point --src at
`cnhkmcp/untracked/APP/Tranformer/template_summary.txt`.

The pieces live in `parse_cnhkmcp_vocab`, `parse_cnhkmcp_reference`,
`parse_cnhkmcp_parse`, `parse_cnhkmcp_classify` and `parse_cnhkmcp_report`;
they are re-exported here so that this entry point keeps working unchanged.

Usage:
    python3 tools/parse_cnhkmcp_templates.py --src /path/to/template_summary.txt
"""

import argparse
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.parse_cnhkmcp_classify import classify, dedupe  # noqa: E402
from tools.parse_cnhkmcp_parse import parse_blocks  # noqa: E402
from tools.parse_cnhkmcp_reference import load_known_non_pv, load_reference  # noqa: E402
from tools.parse_cnhkmcp_report import write_and_report  # noqa: E402
from tools.parse_cnhkmcp_vocab import (  # noqa: E402,F401
    CALL_RE,
    NOISE,
    PLACEHOLDER_RE,
    PREFIX_RE,
    REFERENCE,
    TOKEN_RE,
)

DB = os.path.join(PROJECT_DIR, "brain_data.duckdb")
OUT = os.path.join(PROJECT_DIR, "docs", "forum", "cnhkmcp_curated_templates.json")

_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument("--src", required=True, help="path to cnhkmcp's template_summary.txt")
_ap.add_argument("--out", default=OUT, help="output JSON path")
_ap.add_argument("--db", default=DB, help="brain_data.duckdb path")
_args = _ap.parse_args()

SRC, OUT, DB = _args.src, _args.out, _args.db

if not os.path.exists(SRC):
    raise SystemExit(
        f"source not found: {SRC}\nUnzip the cnhkmcp wheel and pass its untracked/APP/Tranformer/template_summary.txt"
    )

with open(SRC, encoding="utf-8", errors="replace") as fh:
    text = fh.read()

REACHABLE_FIELDS, PV_OPTION_DATASETS = load_reference(DB)
KNOWN_NON_PV = load_known_non_pv()

templates = parse_blocks(text)
classify(templates, REACHABLE_FIELDS, PV_OPTION_DATASETS, KNOWN_NON_PV)

uniq = dedupe(templates)
write_and_report(uniq, OUT)
