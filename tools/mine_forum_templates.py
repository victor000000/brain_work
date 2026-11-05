#!/usr/bin/env python3
"""Mine alpha-expression templates from the harvested forum corpus.

Covers post bodies AND comments. Comments matter: the forum holds ~91k of them
against 8.2k posts, so a posts-only pass sees roughly a tenth of the text.

Pipeline: strip HTML -> pull expression-shaped lines -> reject Python and prose
-> normalise datafields to {f} slots so skeletons cluster -> classify each
skeleton by whether its fields are reachable under the pv/option restriction.

The pieces live in `mine_forum_vocab` (the operator list), `mine_forum_patterns`
(regexes), `mine_forum_text` (line handling), `mine_forum_classify` (reachability),
`mine_forum_scan` (the corpus walk) and `mine_forum_output`/`mine_forum_main`
(writing and reporting); they are re-exported here so `from tools.mine_forum_templates
import ...` keeps resolving for the thought miner and the tests.

Writes docs/forum/forum_templates.json.

Usage:
    python3 tools/mine_forum_templates.py [--db PATH]
"""

import argparse
import os
import sys

sys.stdout.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from tools.mine_forum_classify import DB, classify, load_reference, residual_tokens  # noqa: F401
from tools.mine_forum_main import main
from tools.mine_forum_output import FORUM, OUT, report, write_rows  # noqa: F401
from tools.mine_forum_patterns import (  # noqa: F401
    ANY_OP_RE,
    CALL_RE,
    NON_FIELD,
    PREFIX_RE,
    PY_MARKERS,
    STRONG_RE,
    TOKEN_RE,
)
from tools.mine_forum_scan import build_rows, scan_documents  # noqa: F401
from tools.mine_forum_text import (  # noqa: F401
    balanced,
    html_to_text,
    iter_text,
    looks_like_alpha,
    normalize_expression_line,
    skeletonize,
    strip_comments,
)
from tools.mine_forum_vocab import BRAIN_OPS  # noqa: F401

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Mine alpha-expression templates from the harvested forum corpus.")
    ap.add_argument(
        "--db",
        default=None,
        help="DuckDB file holding the pv/option field reference (default: the live "
        "brain_data.duckdb). Point it at a backup to re-mine while the explorer holds the lock.",
    )
    main(ap.parse_args().db)
