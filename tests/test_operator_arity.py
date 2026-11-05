"""The grammar's real argument shapes, which differ from the documentation.

Several operators document their optional parameters as `name = default` and
then accept them **only by keyword** — a positional call written straight from
the platform's own definition fails validation. The one that bit us:
`hump(x, hump = 0.01)` rejects `hump(x, 0.05)` with
`InvalidPositionalArgumentCount { expected: 1, actual: 2 }` on every render
(found 2026-10-12 by the registry sweep, in a template written from that
definition, before it cost a simulation).

The same audit — every operator's documented parameter list, parsed against
`parse_error` — found the rest of the class, and this pins it. Two of these are
sharper than "keyword-only": `tail` and the `ts_target_tvr_*` pair require
their keywords to be *present*, so the documented defaults do not exist as
defaults at all:

    tail(close)                            MissingKeyword("upper")
    tail(close, upper=0.5, newval=0)       MissingKeyword("lower")
    ts_target_tvr_decay(close)             MissingKeyword("target_tvr")
    kth_element(close, 20)                 MissingKeyword("k")
    ts_backfill(close, lookback=20)        InvalidPositionalArgumentCount expected 2, actual 1

A template or mined skeleton written from the docs without these shapes is
rejected at validation, cost a generation round each time, and never simulates.
"""

import pytest

from generator.validate import parse_error

OPS = {
    "hump",
    "tail",
    "kth_element",
    "ts_target_tvr_decay",
    "ts_target_tvr_hump",
    "rank",
    "normalize",
    "winsorize",
    "bucket",
    "quantile",
    "ts_backfill",
    "trade_when",
    "group_neutralize",
    "ts_delta",
    "close",
    "volume",
    "cap",
    "sector",
    "nan",
}

# (documented-but-rejected call, the shape the grammar takes instead)
KEYWORD_ONLY = [
    ("hump(close, 0.05)", "hump(close, hump=0.05)"),
    ("rank(close, 2)", "rank(close, rate=2)"),
    ("normalize(close, true, 0.0)", "normalize(close, useStd=false, limit=0.0)"),
    # `lower`, `upper` and `newval` are all required keywords.
    ("tail(close, 0, 0, 0)", "tail(close, lower=0, upper=0, newval=0)"),
    ("tail(close)", "tail(close, lower=0, upper=0, newval=0)"),
    ("kth_element(close, 20, 2)", "kth_element(close, 20, k=2)"),
    # The documented `target_tvr = 0.1` is not a default: the keyword is required.
    ("ts_target_tvr_decay(close)", "ts_target_tvr_decay(close, target_tvr=0.1)"),
    ("ts_target_tvr_decay(close, 0, 1, 0.1)", "ts_target_tvr_decay(close, target_tvr=0.1)"),
    ("ts_target_tvr_hump(close)", "ts_target_tvr_hump(close, target_tvr=0.1)"),
    # `lookback` is positional here, not a keyword like the definition spells it.
    ("ts_backfill(close, lookback=20)", "ts_backfill(close, 20)"),
]


@pytest.mark.parametrize(("rejected", "accepted"), KEYWORD_ONLY)
def test_documented_positional_shape_is_rejected_and_the_keyword_form_parses(rejected, accepted):
    assert parse_error(rejected, OPS) is not None, f"{rejected} should not parse"
    assert parse_error(accepted, OPS) is None, f"{accepted} should parse"


def test_the_shapes_already_in_use_still_parse():
    """The forms the registry emits, pinned so a grammar change cannot silence them.

    `winsorize`, `bucket` and `quantile` take their documented parameters by
    keyword and are used that way; `ts_backfill` takes its lookback
    positionally; `trade_when` is three positional arguments. The `bucket` case
    is written in the context the registry uses it in: standalone
    `bucket(rank(cap), range=…)` is rejected as "signal must be
    Matrix-compatible, but got Group" — the checker types `bucket` as a Group
    only where a group is wanted, which is inside the `group_neutralize` call.
    """
    for expr in (
        "winsorize(ts_backfill(close, 63), std=4.0)",
        "group_neutralize(rank(close), bucket(rank(cap), range='0,1,0.1'))",
        "quantile(close, driver='gaussian')",
        "ts_backfill(close, 63)",
        "trade_when(volume > 1, ts_delta(close, 20), -1)",
        "ts_target_tvr_decay(close, target_tvr=0.1, lambda_min=0, lambda_max=1)",
    ):
        assert parse_error(expr, OPS) is None, f"{expr} should parse"
