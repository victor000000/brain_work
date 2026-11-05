"""Regexes and word lists that decide what in a forum post is an expression.

Split out of `tools/mine_forum_templates.py`, which re-exports them.
"""

import re

from tools.mine_forum_vocab import BRAIN_OPS

STRONG_RE = re.compile(
    r"\b(ts_[a-z_]+|group_[a-z_]+|vec_[a-z_]+|winsorize|trade_when|signed_power|"
    r"s_log_1p|pasteurize|days_from_last_change|bucket|rank_by_side)\s*\(",
    re.I,
)
ANY_OP_RE = re.compile(r"\b(" + "|".join(sorted(BRAIN_OPS, key=len, reverse=True)) + r")\s*\(", re.I)
TOKEN_RE = re.compile(r"\b[a-z][a-z0-9_]*\b", re.I)
CALL_RE = re.compile(r"\b[a-z_][a-z0-9_]*\s*\(", re.I)

PY_MARKERS = re.compile(
    r"\b(def |import |print\(|self\.|pd\.|np\.|os\.|lambda |return |for |while |elif |"
    r"\.append|\.add\(|\.items\(|\[.*\]|>>>|http|\.py\b|\.json|\.csv|"
    r"sharpe|fitness|turnover|drawdown|alpha_id|alphaId|select |from |where )",
    re.I,
)
# Non-value words only: operators, constants and group names.
# Named-argument keys are identified by position, never globally ignored.
# Data fields are deliberately NOT listed here — `close`, `sales`, `dividend`
# and friends were, which kept them literal in every skeleton (so they were
# never classified) and let fundamental-bearing templates ship as
# `fillable_from_pv_option=True`.
NON_FIELD = set(BRAIN_OPS) | {
    "true",
    "false",
    "nan",
    "inf",
    "sector",
    "industry",
    "subindustry",
    "market",
    "country",
    "exchange",
    "currency",
    "group",
    "groups",
    "and",
    "or",
    "not",
    "if",
    "else",
    "on",
    "off",
}
PREFIX_RE = re.compile(r"^([a-z]{2,8}\d+)_")
