"""Multi-field combo templates — combine base expressions for complexity.

Unit safety rules:
- multiply: any units OK (product gets combined units)
- add/subtract: MUST have same units — wrap in rank() if mixing
- ts_delta/ts_zscore: preserve input units

Ternary combos removed — 0% submittable rate across 210+ attempts.

The add/subtract rule above was stated but not implemented: every one of these
combiners wrapped the *result* in `rank()`, which normalises the unit of the
output but leaves the operands inside the arithmetic exactly as they were —
`rank(a - b)` still evaluates `a - b` first. The bases these combiners wrap are
arbitrary 2-field shapes over the flat pv/option pool, so `a` and `b` routinely
carry different units and the platform rejected the whole simulation with
`Incompatible unit for input of "subtract" at index 1`. Measured 2026-10-10 from
`simulations.error_message`: unit rejections are 14-21% of every day's
simulations and have not fallen since the `_PRICE_EXCLUDE` work — the combos are
the largest single contributor, with `subtract` (4,506) and `add` (1,266) at
index 1 the two most-named positions. Ranking each operand makes the arithmetic
unit-free, which is what the rule always said to do; the outer `rank()` is kept
so the emitted shape keeps its existing cross-sectional normalisation.
"""


def _r(expr: str) -> str:
    """`expr` as a unit-free cross-sectional rank, for add/subtract operands."""
    return f"rank({expr})"


# 3-field: enhance a 2-field base with a third conditioning factor
COMBO_3F = [
    lambda e, f3, w: f"rank(({e}) * ts_delta({f3}, {w}))",
    lambda e, f3, w: f"rank(({e}) / (rank({f3}) + 0.01))",
    lambda e, f3, w: f"rank(({e}) * rank({f3}))",
    lambda e, f3, w: f"-rank(({e}) * ts_zscore({f3}, {w}))",
    lambda e, f3, w: f"rank({_r(e)} + {_r(f'ts_mean({f3}, {w})')})",
]
COMBO_3F_NAMES = ["3f_delta", "3f_ratio", "3f_scale", "3f_neg_zscore", "3f_mean"]

# (base_template_name, combo_3f_name) pairs with <=0.38 avg |sharpe| and <5% submit rate.
BLOCKED_3F_COMBOS = {
    ("raw_regression_medium", "3f_mean"),
    ("raw_regression_medium", "3f_ratio"),
    ("raw_regression_long", "3f_delta"),
    ("raw_regression_long", "3f_ratio"),
    ("raw_regression_long", "3f_neg_zscore"),
}

# 4-field: combine two independent 2-field signals (both rank-wrapped)
COMBO_4F = [
    lambda e1, e2: f"rank(({e1}) * ({e2}))",
    lambda e1, e2: f"rank({_r(e1)} - {_r(e2)})",
    lambda e1, e2: f"rank({_r(e1)} + {_r(e2)})",
]
COMBO_4F_NAMES = ["4f_product", "4f_diff", "4f_sum"]

# 5-field: triple-factor interaction
COMBO_5F = [
    lambda e1, e2, f5, w: f"rank(({e1}) * ({e2}) * ts_delta({f5}, {w}))",
    lambda e1, e2, f5, w: f"rank(({_r(e1)} - {_r(e2)}) * rank({f5}))",
]
COMBO_5F_NAMES = ["5f_delta", "5f_diff_scale"]
