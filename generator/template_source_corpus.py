"""Mined-corpus paths and labels, and the template mix setting.

Split out of `generator/template_source.py`, which re-exports these names so
`from generator import template_source as ts` keeps seeing them.
"""

from __future__ import annotations

import math
import os

from core.log import get_file_logger

glog = get_file_logger("generator")

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every mined corpus, in order. forum_templates.json holds `{f}`-skeleton
# mining of the community forum; the two cnhkmcp files hold concrete
# expressions mined from the package's skill knowledge. They use an
# `expression` key instead of `skeleton` — `_normalise` folds both into one
# shape so the rest of the module sees a single contract.
TEMPLATE_PATHS = (
    os.path.join(PROJECT_DIR, "docs", "forum", "forum_templates.json"),
    os.path.join(PROJECT_DIR, "docs", "forum", "cnhkmcp_mined_templates.json"),
    os.path.join(PROJECT_DIR, "docs", "forum", "cnhkmcp_curated_templates.json"),
    # Shapes taken from alphas the platform actually accepted — see the file's
    # own comment. Small, and the only corpus here whose entries were chosen
    # for having worked rather than for having been written down somewhere.
    os.path.join(PROJECT_DIR, "docs", "forum", "proven_templates.json"),
    # Help-centre articles — a Zendesk corpus distinct from the community
    # posts `spider_forum.py` walks, and one no other miner reads. Small: 602
    # articles carry 59 expression lines, 11 of them fillable from pv/option.
    os.path.join(PROJECT_DIR, "docs", "forum", "help_center_templates.json"),
    # Shapes mined from the 1,842 alphas that reached their own cell's
    # submission floor — `proven`'s idea (shapes drawn from results, the one
    # corpus that measures like the built-ins) with 46x the supply, because
    # acceptance is rare and the floor is not. Regenerate with
    # `tools/mine_proven_floor.py`; the file records each shape's evidence.
    os.path.join(PROJECT_DIR, "docs", "forum", "proven_floor_templates.json"),
)

# Fraction of generated expressions that come from forum templates rather than
# the curated built-ins. Override with BRAIN_TEMPLATE_MIX.
#
# Kept in step with the Makefile's TEMPLATE_MIX (`make start` sets the env var,
# which wins); the fallback mattered less than the disagreement did, since a run
# started without it got a different mix than one started through make.
DEFAULT_MIX = 0.1

# Corpus label per file, used to attribute a filled expression to the corpus it
# came from. Without it the pool path recorded nothing and every
# template-derived alpha fell through to the regex signatures in
# `storage.track_signatures` — which know the built-ins only — and was stored
# as `unknown`. Fill-time provenance now records these stable labels for
# `template_performance`, including after a sign flip.
_CORPUS_BY_FILE = {
    "forum_templates.json": "forum",
    "cnhkmcp_mined_templates.json": "cnhkmcp",
    "cnhkmcp_curated_templates.json": "curated",
    "proven_templates.json": "proven",
    "proven_floor_templates.json": "provenfloor",
    "help_center_templates.json": "helpcenter",
}


def _corpus_label(path) -> str:
    """Corpus name for a pool file, falling back to its stem for temp paths."""
    base = os.path.basename(os.fspath(path))
    return _CORPUS_BY_FILE.get(base, os.path.splitext(base)[0])


def template_mix() -> float:
    """Configured share of template-derived expressions, clamped to [0, 1]."""
    raw = os.environ.get("BRAIN_TEMPLATE_MIX")
    if raw is None:
        return DEFAULT_MIX
    try:
        value = float(raw)
        if math.isfinite(value):
            return max(0.0, min(1.0, value))
    except ValueError:
        pass
    glog.warning("bad BRAIN_TEMPLATE_MIX=%r, using %s", raw, DEFAULT_MIX)
    return DEFAULT_MIX


def _normalise(rows) -> list[dict]:
    """Rows in `skeleton` shape, tolerating the `expression` key and junk."""
    out = []
    for r in rows:
        if not isinstance(r, dict) or not r.get("fillable_from_pv_option"):
            continue
        skeleton = r.get("skeleton") or r.get("expression")
        # A non-string skeleton (a number, a list) is junk, not a template: it
        # must be skipped here or `clean_skeleton` dies on `.replace` and the
        # whole corpus share is lost for the run.
        if isinstance(skeleton, str) and skeleton:
            out.append({**r, "skeleton": skeleton})
    return out
