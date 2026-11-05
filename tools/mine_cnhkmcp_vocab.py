"""Candidate extraction and field classification for the cnhkmcp miner.

Split out of `tools/mine_cnhkmcp_templates.py`, which re-exports these names.

Anything unconfirmed counts as outside the restriction — conservative, the
same posture as parse_cnhkmcp_templates.py.
"""

import re

NOISE = {
    "region",
    "universe",
    "delay",
    "decay",
    "neutralization",
    "truncation",
    "pasteurization",
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
    "max",
    "rate",
    "filter",
    "constant",
}
TOKEN = re.compile(r"\b([a-z][a-z0-9_]*)\b", re.I)
CALL = re.compile(r"\b([a-z_][a-z0-9_]*)\s*\(", re.I)
CAND = re.compile(r"[A-Za-z_][A-Za-z0-9_.,'\" *+/%=-]*(?:\([^<>]*\))[A-Za-z0-9_.,'\" *+/%()=<>-]{0,300}")
HTML = re.compile(r"<[a-zA-Z/][^<>]*>")


def candidates_from(text):
    text = HTML.sub(" ", text)
    for m in CAND.finditer(text):
        s = m.group(0).strip(" .,'\"")
        # Lone surrogates survive some decode paths; they are never valid.
        s = s.encode("utf-8", "replace").decode("utf-8")
        if 8 <= len(s) <= 300 and "(" in s:
            yield s


def _classify(expr, positive):
    """(pv/option field names, everything else) referenced by an expression."""
    calls = {m.group(1).lower() for m in CALL.finditer(expr)}
    pv, other = set(), set()
    for tok in {m.group(1).lower() for m in TOKEN.finditer(expr)}:
        if tok in NOISE or tok in calls:
            continue
        (pv if tok in positive else other).add(tok)
    return sorted(pv), sorted(other)
