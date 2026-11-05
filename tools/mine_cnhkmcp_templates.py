#!/usr/bin/env python3
"""Mine expression templates from the vendored cnhkmcp tree and the BRAIN learn docs.

Two sources the forum miner does not cover:

  vendor/cnhkmcp/   the cnhkmcp 4.3.8 package — 20+ skills, 40+ knowledge
                    pages, and the feature-implementation data dirs.
  docs/learn/       the BRAIN-website harvest (tools/harvest_learn_docs.py).

Pipeline: walk every text/JSON file -> pull expression-shaped candidates ->
keep the ones py-fastplus parses -> classify each candidate's fields by
scope -> dedupe against everything already mined (forum corpus + curated).

Scope classification is DB-free on purpose: this runs while the explorer
holds brain_data.duckdb, so it uses docs/forum/field_category_reference.json
(the 65 pv/option names + 865 known-foreign names) plus the field names the
forum mining already confirmed. Anything unconfirmed counts as outside the
restriction — conservative, the same posture as parse_cnhkmcp_templates.py.

Known result (2026-10-03): the in-scope yield is tiny — ~13 of ~6,000
parseable expressions, mostly beginner examples and prose fragments; the bulk
of cnhkmcp's material is analyst/fundamental feature templates, out of scope
under the pv/option restriction. Kept as a repeatable sweep, not a goldmine.

The pieces live in `mine_cnhkmcp_ref`, `mine_cnhkmcp_vocab`,
`mine_cnhkmcp_scan` and `mine_cnhkmcp_main`; they are re-exported here so that
the CLI below and every `from tools.mine_cnhkmcp_templates import ...` keep
working.

Writes docs/forum/cnhkmcp_mined_templates.json.

Usage:
    python3 tools/mine_cnhkmcp_templates.py
"""

import sys

sys.stdout.reconfigure(line_buffering=True)

from tools.mine_cnhkmcp_main import main  # noqa: E402
from tools.mine_cnhkmcp_ref import (  # noqa: E402,F401
    CURATED,
    EXISTING,
    FORUM,
    FORUM_DIR,
    LEARN,
    OUT,
    POSITIVE,
    REF,
    VENDOR,
    _read,
)
from tools.mine_cnhkmcp_scan import parses, strings_from, walk_strings  # noqa: E402,F401
from tools.mine_cnhkmcp_vocab import CALL, CAND, HTML, NOISE, TOKEN, _classify, candidates_from  # noqa: E402,F401


def classify(expr):
    return _classify(expr, POSITIVE)


if __name__ == "__main__":
    main()
