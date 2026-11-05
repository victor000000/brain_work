"""Decide whether a mined line's fields are reachable under pv/option.

Split out of `tools/mine_forum_templates.py`, which re-exports these names.
"""

import os
import re

from core.db import connect_for_reading
from tools.mine_forum_candidate import value_tokens
from tools.mine_forum_patterns import CALL_RE, NON_FIELD, PREFIX_RE, TOKEN_RE

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(PROJECT_DIR, "brain_data.duckdb")


def load_reference(db_path=None):
    """(pv/option field ids, pv/option dataset ids) from the pruned DB.

    The DB holds every pv/option field and dataset, so membership is a
    positive test. Anything else that carries a dataset prefix (`mdl216_*`,
    `anl14_*`) is outside the restriction. Unprefixed non-pv names like
    `assets` stay unknown and are skipped rather than guessed at — after the
    prune there is no reference that could resolve them.

    `db_path` overrides the live database — a re-mine can run off the backup
    while the explorer holds the write lock.
    """
    conn = connect_for_reading(db_path or DB)
    fields = {r[0] for r in conn.execute("SELECT id FROM data_fields")}
    datasets = {r[0] for r in conn.execute("SELECT id FROM datasets WHERE category_id IN ('pv','option')")}
    conn.close()
    return fields, datasets


def classify(expr, reference):
    """Split the value tokens into pv/option fields and everything else.

    Every bare identifier must resolve: known pv/option field -> `pv`; an
    identifier whose dataset prefix names a pv/option dataset -> `pv`; anything
    else (a fundamental field like `sales`, an unresolved name, a single-letter
    placeholder left in the line) -> `other`, which makes the skeleton not
    fillable. Call sites are operator names rather than data, so they are
    skipped — only value positions can reference a field.
    """
    fields, datasets = reference
    # `alpha = <expr>`: the leading name is a label for the expression, not a
    # data field. It still becomes a `{f}` slot in the skeleton (the slotter
    # cannot tell labels from fields), so it must not be classified either.
    lhs, eq, rhs = expr.partition("=")
    if eq and re.fullmatch(r"\s*[A-Za-z_][A-Za-z0-9_]*\s*", lhs):
        expr = rhs
    calls = {m.group(0).rstrip().removesuffix("(").strip().lower() for m in CALL_RE.finditer(expr)}
    pv, other = set(), set()
    for tok in set(value_tokens(expr, TOKEN_RE)):
        if tok in NON_FIELD or tok in calls:
            continue
        if tok in fields:
            pv.add(tok)
            continue
        m = PREFIX_RE.match(tok)
        if m and m.group(1) in datasets:
            pv.add(tok)
        else:
            other.add(tok)
    return pv, other


def residual_tokens(skeleton):
    """Value tokens still literal in a skeleton: labels and short variables.

    The slotter only replaces identifiers of two or more characters, so a
    one-letter assignment label (`b=ts_zscore({f},252)`) or a stray variable
    survives into the skeleton. Those are not fields and cannot be filled, so
    their presence disqualifies the skeleton.
    """
    text = skeleton.replace("{f}", " ")
    calls = {m.group(0).rstrip().removesuffix("(").strip().lower() for m in CALL_RE.finditer(text)}
    return {t for t in value_tokens(text, TOKEN_RE) if t not in NON_FIELD and t not in calls}
