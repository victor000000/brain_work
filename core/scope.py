"""The data scope this project operates in: price and options only.

The restriction was applied once as a cleanup (`tools/cleanup_db.py`), and it
did not hold: the pv/option field refresh calls `store_categories`, which
re-inserted all 62 categories, 55 of them out of scope. `data_fields` and
`datasets` stayed clean only because the refresh happens to fetch pv/option
subcategories — nothing forbade the rest.

So the scope is enforced here, at the *write* paths, rather than by remembering
to filter at every read. A one-shot cleanup is a state; a guard is an
invariant.

Import `ALLOWED_CATEGORIES` rather than restating `('pv', 'option')` —
`generator/field_queries.py` and `diversity_picker/pyramid3.py` already share
one copy, and this is the same list.
"""

from __future__ import annotations

import re

ALLOWED_CATEGORIES = ("pv", "option")

_ALLOWED = frozenset(ALLOWED_CATEGORIES)


def in_scope(category) -> bool:
    """True when a category id is inside the scope.

    A category is in scope if it is one of the allowed top-level ids, or a
    child of one — the platform names children `<parent>-<child>`, e.g.
    `pv-price-volume`, `option-option-analytics`.
    """
    if not category:
        return False
    cat = str(category)
    if cat in _ALLOWED:
        return True
    return cat.split("-", 1)[0] in _ALLOWED


def out_of_scope(category) -> bool:
    """Inverse of `in_scope`, for readability at call sites."""
    return not in_scope(category)


def keep_category(row: dict, key: str = "id") -> bool:
    """Predicate for a single category/dataset row from the BRAIN API."""
    return in_scope(row.get(key))


def scope_sql(column: str) -> str:
    """SQL fragment matching in-scope rows, for the category column given.

    Built from ALLOWED_CATEGORIES so the SQL and the Python predicate cannot
    drift apart.
    """
    allowed = ", ".join(f"'{c}'" for c in ALLOWED_CATEGORIES)
    prefixes = " OR ".join(f"{column} LIKE '{c}-%'" for c in ALLOWED_CATEGORIES)
    return f"({column} IN ({allowed}) OR {prefixes})"


# ---------------------------------------------------------------------------
# Semantic input validation (design 2026-11-05, P0)
#
# `in_scope` above guards a *dataset/category row*. It cannot answer the
# question the design actually asks: does every NUMERIC leaf of this expression
# resolve to a permitted measurement? A field can be fetched from an in-scope
# dataset and still be a classifier code, or a GROUP partition used as a number.
# These helpers answer that, and fail closed: an unresolved leaf is "review",
# never "ok".
# ---------------------------------------------------------------------------

# Identifiers that are operators/keywords rather than data leaves. A leaf that
# matches one of these is not evidence of any category.
_OPERATORS = frozenset(
    """
    abs add arc_cos arc_sin arc_tan argmax argmin bucket
    corr count covariance decay delay delta densify divide exp filter
    group_backfill group_count group_max group_mean group_min group_neutralize
    group_normalize group_rank group_scale group_std group_sum group_zscore
    hump if_else inverse jump kth kurt log max mean median min multiply
    nan_mask normalize pasteurize power product quantile rank rank_by
    regression reverse scale sign signed_power sin skew sma sqrt std
    subtract sum tan trade_when ts_arg_max ts_arg_min ts_av_diff ts_backfill
    ts_corr ts_count_nans ts_covariance ts_decay_linear ts_delta ts_delay
    ts_ir ts_kurtosis ts_max ts_max_diff ts_mean ts_median ts_min ts_min_diff
    ts_moment ts_product ts_rank ts_regression ts_returns ts_scale ts_skewness
    ts_std_dev ts_step ts_sum ts_target_tvr_decay ts_target_tvr_hump ts_var
    ts_zscore vec_avg vec_count vec_max vec_min vec_sum winsorize zscore
    """.split()  # noqa: SIM905 - keep the operator vocabulary readable by family
)

_LEAF = re.compile(r"\b([a-z][a-z0-9_]{2,})\b")

# Prefix/idiom -> dataset category. Deliberately conservative: a leaf is only
# classified when its meaning is unambiguous from its name.
_PREFIX_CATEGORY = (
    (
        "pv",
        re.compile(
            r"^(pv\d+_|close$|open$|high$|low$|volume$|vwap$|returns$|cap$|sharesout$|dividend$|split$|adv\d*$|turnover$)"
        ),
    ),
    ("option", re.compile(r"^(opt\d+_|implied_volatility|pcr_|put_call|option)")),
    ("risk", re.compile(r"^(rsk\d+_|idiosyncratic_|resid|beta$|volatility_)")),
    ("model", re.compile(r"^(mdl\d+_|ai_|acquisition_model|ai_factor)")),
    ("analyst", re.compile(r"^(anl\d+_|analyst_|est_|actual_|actuals_)")),
    ("fundamental", re.compile(r"^(fnd\d+_|assets|liabilities|revenue|net_income|equity$|debt|cash)")),
    ("news", re.compile(r"^(nws\d+_|news_|sentiment)")),
    ("institutions", re.compile(r"^(inst\d+_|institution)")),
    ("other", re.compile(r"^(oth\d+_|event_|ern\d+_|mws\d+|qfl_|mdl260_)")),
)

# Categories that are legitimate only as partitions (GROUP inputs), never as
# numeric leaves in a signal.
_PARTITION_ONLY = frozenset({"group", "partition", "classifier"})


def expression_leaves(expr: str):
    """Candidate data leaves of a FASTEXPR string, in first-seen order.

    Operators and keywords are excluded; numbers cannot match the pattern.
    """
    seen, out = set(), []
    for tok in _LEAF.findall(expr or ""):
        if tok in _OPERATORS or tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


# Semantics beat the prefix.
#
# The platform stores some analyst-estimate and fundamental measures under pv*
# ids — e.g. `pv87_ebt_normalized_consensus_high_scale` and
# `pv87_revenue_consensus_median_scale`. A `pv` prefix would otherwise classify
# them as price/volume and let them through the scope guard, which is exactly
# the numeric-leaf misuse P0-1 exists to stop: they are estimates and
# fundamentals, not PV/options value fields. Meaning is therefore checked first.
# Python's \b treats '_' as a word character. Field names use underscores
# between semantic tokens, so explicit alphanumeric boundaries are needed.
_MEANING_CATEGORY = (
    ("analyst", re.compile(r"(consensus|estimate|guidance|analyst|(?<![a-z0-9])eps(?![a-z0-9])|target_price)")),
    (
        "fundamental",
        re.compile(
            r"(revenue|ebitda|(?<![a-z0-9])(?:ebit|ebt|assets)(?![a-z0-9])|net_income|liabilities|book_value|cash_flow|equity_|_equity\b)"
        ),
    ),
)


def classify_leaf(leaf: str):
    """Resolve one leaf to a dataset category, or None when ambiguous.

    None means "we cannot say from the name alone" and must be treated as
    review rather than permitted — `validate_expression` does exactly that.

    Meaning is resolved before the id prefix: a measure whose *name* says it is
    an analyst estimate or a fundamental is never permitted just because its id
    starts with `pv`.
    """
    if leaf:
        for name, rx in _MEANING_CATEGORY:
            if rx.search(leaf):
                return name
    for name, rx in _PREFIX_CATEGORY:
        if rx.match(leaf):
            return name
    return None


def validate_expression(expr, resolver=None):
    """Decide whether an expression's numeric leaves are all permitted.

    Returns a dict:
      status   "ok" | "violation" | "review"
      permitted / blocked / unresolved  -- leaf lists
      detail   {leaf: category}

    `resolver` may override `classify_leaf` (e.g. with DB-resolved field
    metadata). It must return a category string, "group"/"partition" for
    partition-only leaves, or None.

    Fail-closed by design: a leaf that cannot be resolved makes the whole
    expression "review", which the dispatch gate treats as not sendable.
    """
    resolve = resolver or classify_leaf
    detail, permitted, blocked, unresolved = {}, [], [], []
    for leaf in expression_leaves(expr):
        cat = resolve(leaf)
        detail[leaf] = cat
        if cat is None:
            unresolved.append(leaf)
        elif cat in _PARTITION_ONLY:
            blocked.append(leaf)
        elif in_scope(cat):
            permitted.append(leaf)
        else:
            blocked.append(leaf)
    if blocked:
        status = "violation"
    elif unresolved:
        status = "review"
    elif not permitted:
        # No resolvable numeric leaf at all: nothing to send.
        status = "review"
    else:
        status = "ok"
    return {
        "status": status,
        "permitted": permitted,
        "blocked": blocked,
        "unresolved": unresolved,
        "detail": detail,
    }


def dispatch_block_reason(verdict):
    """A human reason when `validate_expression` forbids dispatch, else None.

    Despatch call sites use this so the refusal is recorded verbatim rather
    than inferred from a bare boolean.
    """
    status = (verdict or {}).get("status")
    if status == "ok":
        return None
    if status == "violation":
        return "out-of-scope or partition-only inputs: " + ", ".join(sorted(verdict.get("blocked") or []))
    return "unresolved inputs (semantic review required): " + ", ".join(sorted(verdict.get("unresolved") or []))
