"""Role-unit coherence for the pool-based website templates.

These three roles — price, market cap, return series — were each filled by a
substring search over the datafield pool, so a field whose *name* contained the
role word won the draw whatever its unit:

  `open` matched option open interest (`opt3_openint*`)
  `low`  matched analyst estimate bounds and "flow" (`*_estimate_low`,
         `..._free_cash_flow...`)
  `cap`  matched `capital`, so `pv37_capital_inv_di` — capital investment —
         filled the market-cap role (the cap role had no exclusion list at all)
  `return` matched `return_on_equity`, a fundamental ratio regressed against a
         stock-return series

The platform rejects the result with `Incompatible unit for input of
"subtract" at index 1, ...` — 14-21% of every day's simulations, measured
2026-10-10. These tests pin the role filters so the leaks cannot come back.
"""

import random

from generator.field_picker.cache import FieldCache, set_cache
from generator.templates_brain_website_group_cap import cap_decile_neutralized, capm_beta, capm_residual
from generator.templates_brain_website_pick import (
    _pick_cap,
    _pick_price,
    _pick_price_set,
    _pick_return,
)
from generator.templates_brain_website_price_action import high_low_spread, open_close_ratio, overnight_gap

# Real pv/option field names covering both the leaks and their valid neighbours.
POOL = [
    # genuine prices
    "close",
    "vwap",
    "high",
    "low",
    "open",
    "pv37_close_12",
    "pv141_wq_w_close",
    # leaks: a price word inside another word or a derived bound
    "opt3_openintecallatm",
    "pv87_ann_matrix_net_debt_estimate_low",
    "pv87_qtr_matrix_net_income_normalized_estimate_low",
    "pv20_beforecons_low",
    "pv87_industry_recommendation_high",
    "max_high_price_60m_pre_close_2",
    "pv87_ann_matrix_free_cash_flow_estimate_mean",
    # genuine market caps
    "cap",
    "opt6_mktcap",
    "market_capitalization_current_day_lagged_0",
    "average_market_cap_ashare",
    # leaks: "capital" is not "cap"
    "pv37_capital_inv_di",
    "pv87_capital_expenditure_mean",
    "adv20_usd_capped_100m",
    "paid_in_share_capital",
    "capital_reserve_index_financial",
    # genuine returns
    "returns",
    "pv20_returns15_1001",
    "pv87_mainsession_return",
    # leaks: a return *ratio*, not a return series
    "pv87_return_on_equity_consensus_median",
    "pv87_return_on_assets_of_estimates_scale",
]


def _draw(fn, n=60):
    rng = random.Random(11)
    return {e for e in (fn(POOL, rng) for _ in range(n)) if e is not None}


def test_price_role_refuses_open_interest_and_estimate_bounds():
    """`open` must not match `openint`, `low` must not match `flow` or a bound."""
    rng = random.Random(3)
    for _ in range(200):
        assert _pick_price(POOL, rng, "open") == "open"
        assert _pick_price(POOL, rng, "low") in {"low"}
        assert _pick_price(POOL, rng, "high") == "high"


def test_cap_role_refuses_capital_fields():
    """Only a real market-cap field may fill the cap role."""
    rng = random.Random(5)
    allowed = {"cap", "opt6_mktcap", "market_capitalization_current_day_lagged_0", "average_market_cap_ashare"}
    for _ in range(200):
        assert _pick_cap(POOL, rng) in allowed


def test_return_role_refuses_fundamental_return_ratios():
    """A return *series*, not `return_on_equity`."""
    rng = random.Random(7)
    allowed = {"returns", "pv20_returns15_1001", "pv87_mainsession_return"}
    for _ in range(200):
        assert _pick_return(POOL, rng) in allowed


def test_price_templates_emit_unit_coherent_arithmetic():
    """Every operand of a price spread is a price, for every seed."""
    for fn in (high_low_spread, open_close_ratio, overnight_gap):
        for expr in _draw(fn):
            for leak in (
                "openint",
                "estimate",
                "flow",
                "recommendation",
                "beforecons",
                "max_high",
            ):
                assert leak not in expr, f"{fn.__name__} emitted {expr}"


def test_cap_templates_never_regress_against_capital_expenditure():
    """The cap operand is a real cap field, in all three cap templates."""
    for fn in (capm_residual, capm_beta, cap_decile_neutralized):
        for expr in _draw(fn):
            assert "capital_inv" not in expr, f"{fn.__name__} emitted {expr}"
            assert "expenditure" not in expr, f"{fn.__name__} emitted {expr}"
            assert "capped" not in expr, f"{fn.__name__} emitted {expr}"


def test_capm_market_leg_is_a_return_series():
    """`ts_regression`'s benchmark leg rejects a fundamental ratio.

    Only the regression templates take a *return* leg; `cap_decile_neutralized`
    neutralises an arbitrary signal, and `group_neutralize` has no unit
    constraint on it, so `return_on_assets` is legitimate there.
    """
    for fn in (capm_residual, capm_beta):
        for expr in _draw(fn):
            assert "return_on_" not in expr, f"{fn.__name__} emitted {expr}"


def test_narrow_pool_returns_none_rather_than_a_wrong_unit():
    """A pool with no valid candidate yields None, which callers already handle.

    The alternative — falling back to a field of the wrong unit — is what cost
    the simulations, so degrading to None is the intended behaviour.
    """
    rng = random.Random(13)
    only_leaks = ["opt3_openintecallatm", "pv37_capital_inv_di", "pv87_return_on_equity_consensus_median"]
    assert _pick_price(only_leaks, rng, "open") is None
    assert _pick_cap(only_leaks, rng) is None
    assert _pick_return(only_leaks, rng) is None


def _cache(matrix_by_dataset):
    c = FieldCache()
    c.matrix_by_dataset = matrix_by_dataset
    return c


TWO_DATASETS = {
    "pv98": ["pv98_close_10_backfill", "pv98_vwap_12", "pv98_high_3", "pv98_low_4", "pv98_open_5"],
    "pv37": ["pv37_close_110000", "pv37_vwap", "pv37_high_9", "pv37_low_9", "pv37_open_9"],
}


def test_price_roles_for_one_expression_come_from_one_dataset():
    """The defect the token filter cannot see: two prices, one unit each, mixed.

    389 `subtract`-at-index-1 rejections since 2026-10-08, half of
    `vwap_close_spread`'s output, and the prefix census proves the cause —
    pv37 77, unprefixed 59, pv98 43, pv141 21.
    """
    set_cache(_cache(TWO_DATASETS))
    fields = [f for fs in TWO_DATASETS.values() for f in fs]
    rng = random.Random(4)
    for roles, n in ((("close", "vwap"), 2), (("high", "low", "close"), 3), (("open", "close"), 2)):
        for _ in range(60):
            got = _pick_price_set(fields, rng, *roles)
            assert got is not None and len(got) == n
            datasets = {f.split("_")[0] for f in got}
            assert len(datasets) == 1, f"mixed datasets: {got}"


def test_no_single_dataset_with_every_role_falls_back_rather_than_mixing():
    """A pool split across datasets returns None; the caller keeps its own draw.

    Returning a mixed pair here would be exactly the bug, so None is the
    contract — the templates then fall back to independent `_pick_price` draws,
    which is also what keeps a region from losing the template entirely.
    """
    split = {"pv98": ["pv98_close_10_backfill"], "pv37": ["pv37_vwap"]}
    set_cache(_cache(split))
    fields = [f for fs in split.values() for f in fs]
    assert _pick_price_set(fields, random.Random(5), "close", "vwap") is None


def test_a_field_outside_the_offered_pool_is_never_returned():
    """The index follows the cache; the caller's pool is the contract.

    The cross-cell polish path re-validates against the *target* cell's fields,
    so a field the caller did not offer must not come back.
    """
    set_cache(_cache(TWO_DATASETS))
    offered = TWO_DATASETS["pv98"]
    for _ in range(40):
        got = _pick_price_set(offered, random.Random(6), "close", "vwap")
        assert got is None or all(f in offered for f in got)


def test_the_open_role_refuses_window_prices():
    """`open` also matches `..._post_open`, and the template is an overnight gap.

    Rendering it 400 times per cell drew a post-open window price in 27-51% of
    fills, so `overnight_gap` was emitting a 30-60 minute intraday move. Every
    cell holds a true open, so refusing the window spellings costs no fill.
    """
    pool = [
        "open",
        "pv37_open_12",
        "high_price_60m_post_open",
        "vwap_30m_post_open",
        "pre_open_price",
    ]
    rng = random.Random(8)
    for _ in range(200):
        got = _pick_price(pool, rng, "open")
        assert got is not None
        assert "post_open" not in got and "pre_open" not in got, got


def test_the_open_exclusion_reaches_the_same_dataset_picker():
    """`_pick_price_set` runs first, so its index must apply the same rule.

    It did not, and the fix was a no-op in every cell where a single dataset
    could supply the roles — which is most of them.
    """
    split = {
        "pv98": ["pv98_open", "pv98_close_10_backfill"],
        "pv37": ["pv37_high_price_post_open", "pv37_close_110000"],
    }
    set_cache(_cache(split))
    fields = [f for fs in split.values() for f in fs]
    rng = random.Random(9)
    for _ in range(60):
        got = _pick_price_set(fields, rng, "open", "close")
        assert got is None or "post_open" not in got[0], got


def test_the_close_role_is_unchanged_by_the_open_exclusion():
    """The rule is scoped to `open` — `pre_close` is a separate open question."""
    pool = ["close", "pv37_close_60m_pre_close_2", "open"]
    rng = random.Random(10)
    seen = {_pick_price(pool, rng, "close") for _ in range(80)}
    assert "open" not in seen
