"""Decide, per template, whether pv/option data alone can fill it.

Split out of `tools/parse_cnhkmcp_templates.py`, which re-exports these names.
"""

import re

from tools.parse_cnhkmcp_vocab import CALL_RE, NOISE, PLACEHOLDER_RE, PREFIX_RE, TOKEN_RE


def classify(templates, reachable_fields, pv_option_datasets, known_non_pv) -> None:
    """Annotate each template in place with its field split and verdict."""
    for t in templates:
        expr = t["expression"]
        if PLACEHOLDER_RE.search(expr):
            # Open `<window>`/`<field>` slots: the template needs a user-supplied
            # input, so it is not fillable from pv/option data alone.
            t["pv_option_fields"] = []
            t["other_fields"] = ["<placeholder>"]
            t["fillable_from_pv_option"] = False
            continue

        # Only value positions can reference a field; call sites are operators.
        calls = {m.group(1).lower() for m in CALL_RE.finditer(expr)}
        pv, other = set(), set()
        for tok in {m.group(1).lower() for m in TOKEN_RE.finditer(expr)}:
            if tok in NOISE or tok in calls:
                continue
            if tok in reachable_fields:
                pv.add(tok)
                continue
            if tok in known_non_pv:
                other.add(tok)
                continue
            m = PREFIX_RE.match(tok)
            if m and m.group(1) not in pv_option_datasets:
                other.add(tok)
                continue
            # Right shape (pvan_*, opt_*, pcr_*) but not in the pruned DB: the
            # reference cannot confirm it, so it is not assumed reachable.
            other.add(tok)
        t["pv_option_fields"] = sorted(pv)
        t["other_fields"] = sorted(other)
        t["fillable_from_pv_option"] = not other


def dedupe(templates):
    """Drop repeated expressions, keeping the first occurrence."""
    seen = set()
    uniq = []
    for t in templates:
        key = re.sub(r"\s+", "", t["expression"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(t)
    return uniq
