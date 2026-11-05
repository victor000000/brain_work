"""Keyword field pickers shared by the pool-based BRAIN website templates.

Split out of `generator/templates_brain_website.py`, which re-exports these
names so `from generator.templates_brain_website import ...` keeps resolving.
"""

import re

# A raw traded-volume field must not be one of the derived ratios or averages —
# dividing a ratio by an average is not the volume-surge signal it looks like.
# A volume-weighted price still has a whole ``volume`` token. The recorded
# session_1430to1430_volume_weighted_avg_price is native PV103 VWAP, not a
# traded-volume series, so reject explicit price/VWAP roles as well.
_RAW_VOLUME_EXCLUDE = ("ratio", "average", "adv", "price", "vwap")

# The "average volume" role no longer has a keyword list. `volume_ratio` was
# the only member most cells could supply — 40 of 46 (region, universe, delay)
# combos carry no `adv` or `average_daily_trading_volume` field at all — and a
# `*_volume_ratio_*` field is already volume-over-average, so dividing or
# comparing a volume by it is not the surge signal it reads as. The three
# templates that wanted an average now take `ts_mean` of the volume field
# itself (`templates_brain_website_volume.py`), which is unit-safe everywhere
# and needs no second pick.

# What a raw *price* role must refuse. `_pick` matches on substrings, so every
# derived measure whose name merely spells a price word used to win the draw:
# measured over the 7,728 field tokens in brain_logs/alpha.log*, `vwap` matched
# 155 names of which 55 are `*_to_vwap_ratio_*`, `low` matched 295 including
# `mean_low_ask_size_1min`, and `close` matched 164 including
# `mean_slippage_30m_pre_close`. In a template whose arithmetic assumes two
# prices — a spread, a ratio, a difference — that is not a suboptimal field but
# a unit-incoherent expression: `(second_high_price_top_book -
# mean_low_ask_size_1min) / pv98_close_1430` (sh=-0.37) subtracts a share count
# from a price, and `(pv37_close_110000 - momentum_bid_to_vwap_ratio_last_half)
# / momentum_bid_to_vwap_ratio_last_half` (sh=-0.01) divides a price by a
# ratio. The platform accepts both (units are only enforced for `group_*` and
# ts_* inputs), so nothing rejected them: scanning the recorded expressions for
# this derived-measure vocabulary finds an operand match in 650 of 1313
# `high_low_spread` and 661 of 1506 `vwap_close_spread` alphas (2026-10-09),
# about half of each template's output. A literal `close`/`vwap`/`high`/`low`/
# `open` is always in a pv pool, so refusing the derived names costs no fill.
_PRICE_EXCLUDE = (
    "ratio",
    "corr",
    "spread",
    "slippage",
    "size",
    "volume",
    "count",
    "score",
    "fraction",
    "likelihood",
    "probability",
    "bucket",
    "flag",
    "return",
    # The pv98 snapshot dataset spells it in the plural, and the check is
    # whole-token, so `"return"` never matched it. Exactly one field leaked
    # through the whole USA/TOP3000/d1 pool —
    # `pv98_vwap_15m_delay_minus_1_returns_returns_fast_d1`, used 15 times
    # since 10-08, including as the VWAP-high role in `vwap_max_strength`.
    "returns",
    "consensus",
    "modulo",
    "capped",
    # Derived statistics over prices, not prices. `max_high_price_60m_pre_close_2`
    # is a rolling high, `mean_low_ask_price_1min` an average quote — neither is
    # the share price the templates' arithmetic assumes.
    "estimate",
    "max",
    "min",
    "mean",
    "median",
    "avg",
    "average",
    "std",
    "dev",
    "deviation",
    "sum",
    "zscore",
    "rank",
    "delta",
    "diff",
    "growth",
    "surprise",
    "target",
    "amount",
    "traded",
    "weight",
    "number",
    # Non-price vocabulary that a price word can hide inside. `low` is a
    # substring of "flow", so `..._free_cash_flow_estimate_mean` used to fill
    # the low-price slot of `(high - low) / close`.
    "net",
    "income",
    "debt",
    "revenue",
    "cash",
    "flow",
    "inv",
    "capital",
    "reserve",
    "openint",
    # Analyst estimate bounds spelled without the word "estimate", and the
    # recommendation-derived bounds. Found by rendering the price-role
    # templates against the USA pool after the token fix: `high_low_spread`
    # was still emitting `(pv87_industry_recommendation_high - low) / close`
    # and `(high - pv20_beforecons_low) / close` — a recommendation score and a
    # pre-consensus estimate bound standing in for traded prices.
    "recommendation",
    "beforecons",
    "aftercons",
)

# `_pick` matches keywords as substrings, which is right for the loose roles
# (a "return" role wants `returns`, `total_return`, ...) and wrong for the two
# roles whose arithmetic assumes a particular *unit*. Measured 2026-10-10 over
# the recorded expressions, substring matching still leaked three families past
# the 2026-10-09 fix: `open` matched option open interest (`opt3_openint*`),
# `low` matched analyst estimate bounds (`*_estimate_low`) and "flow", and
# `high` matched the same estimate family. Token matching kills the fragment
# case outright — `open` is not a token of `openintecallatm` — and the exclude
# list above covers the derived names that are still spelled as real tokens.
# Single-interval fields, rescued by a backfill at the pick — in HKG only,
# where the measurement lives.
#
# `pv37_<measure>_<stamp>` is one intraday timestamp's value, not a session
# aggregate (`session_1430to1430_*`, `*_30m_pre_close_*`); through a
# day-frequency template (a surge ratio, a 20-day z-score, a 250-day
# ts_rank) the series is sparse for HKG names on some days, and the sparse
# book is what CONCENTRATED_WEIGHT reads. Measured 2026-10-15 against the
# parked-state backup, HKG/TOP800/d1 alphas at sharpe >= 1.58 since 10-12:
# expressions carrying one of these fields fail the check **28 of 82 (34%)**
# against 1 of 14 (7%) without one, and in every other region the same
# families fail 0.1% or less — the interaction is HKG's alone. The
# platform's own help centre names the mechanism and the fix ("data at
# certain timestamps... a large reduction in coverage for these days...
# filling operators like ts_backfill or group_backfill"). Wrapping is
# identity for a series with no gaps, so nothing changes on the days that
# already had data; excluding the family instead was rejected — every
# fully-clean HKG alpha since 10-05 carries one of these fields,
# `pv37_close_12` and `pv37_cap_1430` among them, so the family is the
# account's earning population, not its liability.
_INTERVAL_STAMP = re.compile(r"^pv37_.*_[0-9]+$")
# `winsorized_signal`'s cleaning depth.
_BACKFILL_DAYS = 63


def _maybe_backfill(field):
    """`ts_backfill(field, 63)` for an HKG single-interval pv37 field.

    Gated on the loaded region (the cache's `last_loaded`): the failure
    record the predicate above documents is HKG's, and every other
    region's and every unloaded pool's emissions stay byte-identical.
    """
    if not field or not _INTERVAL_STAMP.match(field):
        return field
    # Lazy import, for the reason `_price_role_index` gives.
    from generator.field_picker import get_cache

    loaded = get_cache().last_loaded
    if not loaded or loaded[0] != "HKG":
        return field
    return f"ts_backfill({field}, {_BACKFILL_DAYS})"


_WORD = re.compile(r"[^a-z0-9]+")


def _tokens(name: str) -> set:
    """Lowercased alphanumeric tokens of a field name."""
    return {t for t in _WORD.split(name.lower()) if t}


def _pick_tokens(fields, rng, keywords, exclude=()):
    """Random field with a whole-token keyword match, or None.

    Unlike `_pick`, a keyword must appear as a complete token: `low` matches
    `..._low` and `..._low_2` but not `..._flow...`.
    """
    keys, banned = set(keywords), set(exclude)
    matches = [f for f in fields if (_tokens(f) & keys) and not (_tokens(f) & banned)]
    return _maybe_backfill(rng.choice(matches)) if matches else None


def _pick(fields, rng, *keywords, exclude=()):
    """Random field matching any keyword, or None when the pool has none.

    `exclude` beats `keywords`, so the raw-volume pick can refuse the derived
    `volume_ratio` fields while the average-volume pick asks for them.
    """
    matches = [f for f in fields if any(k in f.lower() for k in keywords) and not any(x in f.lower() for x in exclude)]
    return _maybe_backfill(rng.choice(matches)) if matches else None


# The `open` role wants the day's *opening* price, and the token `open` also
# matches every window measured from it — `high_price_60m_post_open`,
# `vwap_30m_post_open`, and the pre-open spellings. Those are prices, so
# nothing rejected them and nothing flagged them: `overnight_gap` simply
# emitted `{post-open window price} / ts_delay({close}, 1) - 1`, which is a
# 30-60 minute intraday move rather than an overnight gap.
#
# Measured 2026-10-10 by rendering the template 400 times per cell: the role
# drew a `post_open` field in 27-51% of fills (ASI 50%, IND 51%, HKG 34%,
# USA 29%). Every configured cell also holds at least one true open — USA 3,
# HKG 8, CHN 1, ASI 1, AMR 2, and GBR/DEU 1 each — so refusing the window
# spellings costs no cell the template.
_OPEN_WINDOW_TOKENS = ("post", "pre")


def _pick_price(fields, rng, *keywords):
    """A raw price for a role whose arithmetic assumes one.

    Used by multi-operand price arithmetic and by templates that explicitly
    derive stock returns as close / previous close - 1. That ratio is unit-free
    even for a non-price input, but a modulo-price statistic's change is not
    a stock return. Native leMjLOjO demonstrated that semantic leak. Generic
    any-field transforms keep `_pick` and their full field diversity.

    The `open` role additionally refuses the window spellings — see
    `_OPEN_WINDOW_TOKENS`. The `close` role does not yet, and the same
    question is open there: `..._60m_pre_close_2` and
    `market_close_auction_clearing_price` are the close of a window rather than
    of the day. Not measured yet, and not changed on a guess.
    """
    exclude = _PRICE_EXCLUDE
    if "open" in keywords:
        exclude = (*_PRICE_EXCLUDE, *_OPEN_WINDOW_TOKENS)
    return _pick_tokens(fields, rng, keywords, exclude)


# What a market-cap role must refuse. `cap` was never covered by the price fix
# and used plain `_pick(fields, rng, "cap")`, so "capital" matched: every fill
# observed in the logged corpus was a capital-expenditure or capital-investment
# field (`pv37_capital_inv_di`, `pv87_capital_expenditure_*`) or
# `adv20_usd_capped_100m`. `cap_decile_neutralized` was therefore neutralising
# within *capex* deciles and `capm_beta` regressing against a capex-weighted
# "market" — neither does what its docstring says.
_CAP_EXCLUDE = ("capped", "expenditure", "inv", "reserve", "paid", "additional", "bet", "gp", "index_cap")

# `cap` is the platform's own market-cap field; `mktcap` is the options
# dataset's. The two-token spellings (`market_capitalization_*`,
# `average_market_cap_ashare`) are matched by `_pick_cap` below, because
# neither carries a bare `cap` token.
_CAP_TOKENS = ("cap", "mktcap")


def _pick_cap(fields, rng):
    """A market-capitalisation field for the cap role, or None."""
    cap = _pick_tokens(fields, rng, _CAP_TOKENS, _CAP_EXCLUDE)
    if cap is not None:
        return cap
    # `market_capitalization_current_day_lagged_0` and its siblings spell the
    # concept out; require both tokens so `capital_reserve_index_financial` and
    # `paid_in_share_capital` cannot pass.
    spelled = [
        f
        for f in fields
        if {"market", "cap"} <= _tokens(f)
        or {"market", "capitalization"} <= _tokens(f)
        or {"market", "capitalisation"} <= _tokens(f)
        or {"firm", "capitalization"} <= _tokens(f)
    ]
    spelled = [f for f in spelled if not (_tokens(f) & set(_CAP_EXCLUDE))]
    return rng.choice(spelled) if spelled else None


# What a *return series* role must refuse when it stands in for the market leg
# of a regression. `_pick(fields, rng, "return")` matches by substring, so
# `pv87_return_on_equity_consensus_median` and `pv87_return_on_assets_of_...`
# won the draw — a fundamental ratio regressed against a stock-return series,
# which the platform rejects at `ts_regression` index 1 (2,120 recorded
# rejections, the third-largest unit-error shape). `mainsession_return`,
# `total_return` and the bare `returns` field all survive the filter.
_RETURN_EXCLUDE = (
    "on",
    "equity",
    "asset",
    "assets",
    "capital",
    "invested",
    "consensus",
    "estimate",
    "median",
    "mean",
    "low",
    "high",
    "growth",
    "surprise",
    # The same leak, one vocabulary further out: a name that merely mentions a
    # return is not a return series. Over USA/TOP3000/d1's 299 substring
    # matches these tokens were still winning the draw — `likelihood_fifth_
    # return_bucket_bidaskr10` (a probability), `interval_cumulative_return_
    # volume` and `..._return_price` (a volume and a price),
    # `interval_standard_deviation_return` (a dispersion), and
    # `predicted_ten_day_forward_return`, which is what `capm_beta` actually
    # regressed against on 2026-10-10 — a model output, not a realised return.
    "likelihood",
    "probability",
    "bucket",
    "volume",
    "price",
    "predicted",
    "prediction",
    "expected",
    "forecast",
    "standard",
    "deviation",
    "std",
    "sigma",
    "variance",
)


def _pick_return(fields, rng):
    """A return series, for a leg whose arithmetic assumes returns.

    Keyword matching stays a substring test here — `returns15` is one token and
    a whole-token match on `return` would miss it — because for this role the
    leak was never the keyword: `return_on_equity` is caught by excluding its
    *other* tokens, not by refusing to see "return" inside it.
    """
    banned = set(_RETURN_EXCLUDE)
    matches = [f for f in fields if "return" in f.lower() and not (_tokens(f) & banned)]
    return rng.choice(matches) if matches else None


def _pick_iv_skew_pair(fields, rng):
    """(`call`, `put`) implied-volatility fields of one tenor from one dataset.

    The skew is call IV minus put IV *at the same maturity*: subtracting across
    tenors measures term structure, not skew, and its sign flips depending on
    which pair the draw lands on. Pairs are found by name, so both spellings in
    the pool work — option8's `implied_volatility_call_20` /
    `implied_volatility_put_20` and option40's `opt40_ivcall20` /
    `opt40_ivput20` — by requiring that replacing `call` with `put` in a call
    field's name names a field that exists.

    The name filter is `volatilitycall`/`ivcall` on the underscore-stripped
    name, not a substring `iv`: pv87 carries 6,138 option fields whose names
    hold `ivy` and `oigammacall` (gamma by open interest), and a call/put pair
    of *those* is a greeks spread wearing the same clothes.
    """
    present = set(fields)
    pairs = []
    for f in fields:
        flat = f.lower().replace("_", "")
        if "volatilitycall" not in flat and "ivcall" not in flat:
            continue
        mirror = f.replace("call", "put", 1)
        if mirror in present:
            pairs.append((f, mirror))
    return rng.choice(pairs) if pairs else None


# The group argument of a `group_*` operator is a *grouping*, not a datafield:
# `sector`, `industry` and `subindustry` are the platform's own built-in
# groups. Sourcing it with `_pick` searched the datafield pool instead, and any
# field whose name merely mentions industry matched — HKG's pool holds
# `pv37_gics_industry_group_number_di`, a plain MATRIX. The platform then
# rejected the simulation with `Incompatible unit for input of "group_rank" at
# index 1, expected "Unit[Group:1]", found "Unit[]"` (observed live
# 2026-10-06), costing a simulation slot each time. `group_rank_diff` in
# templates_cnhkmcp_canonical already picks a literal group name; this matches
# that.
_GROUP_NAMES = ("sector", "industry", "subindustry")


def _pick_group(rng):
    """A built-in grouping field, for a `group_*` operator's group argument."""
    return rng.choice(_GROUP_NAMES)


# The price roles a multi-operand template can ask for, all at once. Fixed, so
# the per-dataset index below can be built once per field load for exactly
# these.
_PRICE_ROLES = ("close", "vwap", "high", "low", "open")

# dataset id -> role -> [field], and the `matrix_by_dataset` identity it was
# built from. Keyed on identity rather than on the cache, for the reason
# `random_generator_dispatch._field_pool` gives: `load_all_fields` *rebinds*
# `matrix_by_dataset` when the region changes, so a cache-keyed index would
# hand every later region the first region's datasets.
_price_roles: dict[str, dict[str, list[str]]] = {}
_price_roles_source = None


def _price_role_index():
    """`dataset -> role -> price fields` for the current region's pool."""
    global _price_roles, _price_roles_source
    from generator.field_picker import get_cache

    matrix = get_cache().matrix_by_dataset
    if matrix is _price_roles_source:
        return _price_roles
    banned = set(_PRICE_EXCLUDE)
    built: dict[str, dict[str, list[str]]] = {}
    for dataset, fields in matrix.items():
        per_role: dict[str, list[str]] = {}
        for f in fields:
            toks = _tokens(f)
            if toks & banned:
                continue
            for role in _PRICE_ROLES:
                # The `open` role refuses the window spellings here too, or the
                # same-dataset path would reintroduce exactly what
                # `_OPEN_WINDOW_TOKENS` was added to stop — it runs *first*, so
                # `_pick_price`'s exclusion would almost never be reached.
                if role == "open" and toks & set(_OPEN_WINDOW_TOKENS):
                    continue
                if role in toks:
                    per_role.setdefault(role, []).append(f)
        if per_role:
            built[dataset] = per_role
    _price_roles, _price_roles_source = built, matrix
    return _price_roles


def _pick_price_set(fields, rng, *roles):
    """One price per role, all drawn from a *single* dataset.

    `_pick_price` draws each operand independently and filters on name tokens
    only, so it has no notion of which dataset a field came from. Two operands
    that are each "a close" and "a vwap" then meet at `subtract`, which the
    platform gates on units:

        Incompatible unit for input of "subtract" at index 1,
        expected "Unit[CSPrice:1]", found "Unit[]".

    389 of those since 2026-10-08, **every one at index 1**, and half of
    `vwap_close_spread`'s own output. The prefix census is the proof that the
    cause is dataset mixing: pv37 77, unprefixed 59, pv98 43, pv141 21.

    One dataset's fields share a unit, so drawing the whole expression's
    operands from one dataset is what makes the arithmetic coherent. Only
    datasets that can supply *every* requested role are eligible, which is
    also what keeps the output from collapsing to the one canonical
    `close`/`vwap`/`high`/`low`/`open` set everywhere: a dataset rich enough to
    supply the roles is picked, and which one varies per draw.

    Returns a tuple of one field per role, or None when no single dataset can
    supply them all — the caller then falls back to independent `_pick_price`
    draws, so no region loses a template to this.
    """
    allowed = set(fields)
    index = _price_role_index()
    complete = [ds for ds, per_role in index.items() if all(per_role.get(r) for r in roles)]
    if not complete:
        return None
    per_role = index[rng.choice(complete)]
    chosen = tuple(rng.choice(per_role[r]) for r in roles)
    # The index follows the *cache*, and a caller can hand this a different
    # pool — the cross-cell polish path re-validates against the target cell's
    # fields. A field the caller did not offer is not a candidate. The
    # membership test runs on the raw names; the wrap comes after it.
    if not all(f in allowed for f in chosen):
        return None
    return tuple(_maybe_backfill(f) for f in chosen)
