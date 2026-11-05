"""Per-cell sign exploration, so a region that inverts its signals is usable.

The generator never explores the *orientation* of what it emits. Only ~12-13%
of stored expressions carry a leading minus in any region, and several
templates are hard-coded positive — `vwap_close_spread`, `high_low_spread`,
`combo_4f_sum/diff/product` are all 0.0% negative. Orientation is fixed by the
template, so a cell whose realised sharpe is negative can only be learned as
"bad", and `cell_priors` suppresses it.

That is the wrong reading when the *sign* is what is wrong. Measured
2026-10-10, CHN's mean IS sharpe is -0.93 against +0.07 (EUR), +0.04 (USA) and
+0.08 (HKG), and across the 50 templates with >=100 alphas in both CHN and
elsewhere the correlation between a template's CHN mean sharpe and its mean
sharpe elsewhere is **-0.56**, monotonically — the shapes that do best
elsewhere do worst here. `(close - vwap) / vwap`, the classic intraday
reversal, returns -7.00 in CHN against -0.28 in HKG for the same expression.

Negating recovers a positive sharpe, verified live in one multi-sim batch with
identical settings within each pair: -7.00 -> +3.77, -3.53 -> +1.46,
-3.01 -> +0.55, four of five pairs flipping.

The flip is not an exact negation. Later paired measurements refuted the
initial turnover-drag explanation recorded in TODO.md; the residual does not
justify a predictive correction. The policy explores both orientations in a
region with enough negative-mean evidence, retaining half the candidates in
their original orientation. A negative mean alone does not prove that every
template improves when negated.

Off by default for every cell that does not clear the evidence bar, so nothing
outside a demonstrably inverted cell changes behaviour. `BRAIN_SIGN_FLIP_MIX`
overrides the probability; `BRAIN_SIGN_FLIP=0` disables the whole policy.
"""

import math
import os

from core.log import get_file_logger
from core.time_sql import utc_timestamp_sql
from generator.validate import parse_error
from generator.weighted_selection import peek_expr_template, record_expr_template

glog = get_file_logger("generator")

# Only a cell with this much recent evidence is judged at all. The bar is high
# because the policy changes what every batch emits, and a cell short of it
# behaves exactly as it did before.
MIN_SAMPLES = 500

# Mean IS sharpe at or below which a cell is treated as inverted. CHN measures
# -0.93 all-time and -1.47/-1.86 in October; every other region sits within
# +-0.2 of zero, so the gap either side of this threshold is wide.
INVERTED_MEAN_SHARPE = -0.5

# Share of that cell's candidates emitted negated. Half, not all: the flip is
# lossy and the cell is not uniformly wrong — CHN produced a 2.48 alpha on
# 2026-10-10 — so exploring both orientations beats committing to either.
DEFAULT_FLIP_MIX = 0.5

# How far back the mean is measured. Recency matters: the platform's CHN
# behaviour is what is being tracked, not the account's April-May history.
WINDOW_DAYS = 30

# region -> probability that a candidate for it is emitted negated.
_policy: dict[str, float] = {}
_measured: dict[str, tuple[int, float]] = {}


def _window_start(days: int) -> str:
    """UTC date `days` back, compared with normalized platform instants."""
    import datetime

    return (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")


def flip_mix() -> float:
    """Configured share of an inverted cell's candidates to negate."""
    raw = os.environ.get("BRAIN_SIGN_FLIP_MIX")
    if raw is None:
        return DEFAULT_FLIP_MIX
    try:
        value = float(raw)
        if math.isfinite(value):
            return max(0.0, min(1.0, value))
    except ValueError:
        pass
    glog.warning("bad BRAIN_SIGN_FLIP_MIX=%r, using %s", raw, DEFAULT_FLIP_MIX)
    return DEFAULT_FLIP_MIX


def _enabled() -> bool:
    return os.environ.get("BRAIN_SIGN_FLIP", "1") not in ("0", "", "false", "False")


def load_sign_policy(conn) -> None:
    """Rebuild the per-region flip policy from stored outcomes."""
    global _policy, _measured
    _policy, _measured = {}, {}
    if not _enabled():
        return
    try:
        rows = conn.execute(
            "SELECT region, COUNT(*), AVG(is_sharpe) FROM alpha_results "
            f"WHERE is_sharpe IS NOT NULL AND {utc_timestamp_sql('created_at')} >= CAST(? AS TIMESTAMP) "
            "GROUP BY region",
            (_window_start(WINDOW_DAYS),),
        ).fetchall()
    except Exception as e:
        glog.warning("sign policy: could not read outcomes (%s); staying off", e)
        return

    mix = flip_mix()
    for region, n, mean in rows:
        if not region or mean is None:
            continue
        _measured[region] = (int(n), float(mean))
        if int(n) >= MIN_SAMPLES and float(mean) <= INVERTED_MEAN_SHARPE:
            _policy[region] = mix
    if _policy:
        glog.info(
            "sign policy: %s",
            ", ".join(
                f"{r} p={p:.2f} (n={_measured[r][0]}, mean={_measured[r][1]:.2f})" for r, p in sorted(_policy.items())
            ),
        )


def negation_probability(region: str) -> float:
    """Probability that a candidate for `region` should be emitted negated."""
    return _policy.get(region, 0.0)


def measured(region: str):
    """`(n, mean sharpe)` behind the decision for `region`, or None."""
    return _measured.get(region)


def maybe_negate(expr: str, rng, region: str) -> str:
    """`expr`, negated for an inverted cell with the policy's probability.

    Provenance is re-keyed rather than left behind: the template path records
    `expr -> template name` at fill time, the map is keyed by the expression
    *string*, and storage reads it back by that string. Negating without moving
    the entry would store the alpha as `unknown` — the name nothing weights —
    which is the exact defect fixed on 2026-10-08.

    A negation that does not parse is discarded and the original kept. It
    should not happen (`-(...)` is sound for any sound expression), and the
    generator validates the result either way, but a rejected candidate costs a
    whole generation round.
    """
    p = negation_probability(region)
    if p <= 0.0 or expr is None:
        return expr
    if rng.random() >= p:
        return expr
    negated = f"-({expr})"
    if parse_error(negated) is not None:
        return expr
    # `peek`, never `lookup`: the latter *consumes*, and the map is keyed by
    # the expression string while a slotless template emits the same string on
    # every draw — `(close - vwap) / vwap` is CHN's `vwap_close_spread` every
    # time. A consuming read attributes the first draw and leaves every later
    # one to the regex fallback, which has no pattern for pure arithmetic, so
    # they were stored as `unknown` — the name nothing weights. That is the
    # exact defect `peek_expr_template` was written for, and this call
    # reintroduced it when the policy landed.
    name = peek_expr_template(expr)
    if name is not None:
        record_expr_template(negated, name)
    return negated
