"""Volume and options templates for the BRAIN website registry.

Split out of `generator/templates_brain_website.py`, which re-exports these
names so `from generator.templates_brain_website import ...` keeps resolving.
"""

from generator.templates_brain_website_pick import (
    _RAW_VOLUME_EXCLUDE,
    _pick,
    _pick_iv_skew_pair,
    _pick_price,
    _pick_tokens,
)


def volume_surge(fields, rng):
    """Volume relative to recent average - liquidity signal."""
    # Whole-token, not substring: `_pick` matched "volume" inside
    # `..._first_quarter_volumeclock`, so the volume role was filled with a
    # *price* (measured 2026-10-10: `mean_high_price_first_quarter_volumeclock`
    # in `volume_gated_momentum`). The signal is self-consistent either way,
    # which is why nothing rejected it — it just is not a volume.
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if volume is None:
        return None
    # The average is taken from the same field. `_AVG_VOLUME_KEYWORDS` used to
    # supply it and `volume_ratio` is the only member most cells have — 40 of
    # 46 (region, universe, delay) combos have no `adv` or
    # `average_daily_trading_volume` field at all — but a `*_volume_ratio_*`
    # field is already volume-over-average, so `volume / ratio` is a rescaled
    # volume, not a surge. Measured: 9 of this template's 40 stored alphas,
    # e.g. `rank(volume / pv141_volume_ratio_wq_w_close_market)`.
    window = rng.choice([20, 40, 60])
    return f"rank({volume} / ts_mean({volume}, {window}))"


def volume_gated_momentum(fields, rng):
    """Momentum signal gated by volume.

    Covers the pv/option catalog's `volume_gated_signal`, which draws the same
    three operands and emits the same expression; registering both would only
    double the shape's weight.
    """
    close = _pick(fields, rng, "close")
    # Whole-token, not substring: `_pick` matched "volume" inside
    # `..._first_quarter_volumeclock`, so the volume role was filled with a
    # *price* (measured 2026-10-10: `mean_high_price_first_quarter_volumeclock`
    # in `volume_gated_momentum`). The signal is self-consistent either way,
    # which is why nothing rejected it — it just is not a volume.
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if close is None or volume is None:
        return None
    window = rng.choice([20, 40, 66])
    # The average is taken from the *same* field rather than from a second
    # draw. Two independent picks meet at `greater`, which the platform gates
    # on units, and the pool cannot supply matching ones: `_AVG_VOLUME_KEYWORDS`
    # accepts `volume_ratio` fields, and a ratio is `Unit[]` against a volume's
    # `Unit[CSShare:1]`; the pv1 `adv20` is dollar volume (`Unit[CSPrice:1,
    # CSShare:1]`) in the same cells where the volume role draws a share count.
    # 32 `greater`-at-index-1 unit warnings since 10-08, all of them this
    # template. `ts_mean` of the field it is compared against cannot mismatch.
    return f"trade_when({volume} > ts_mean({volume}, {window}), ts_delta({close}, {window}), -1)"


def options_pcr_volume_gated(fields, rng):
    """Put/call open interest ratio only on high volume days."""
    # Whole-token, not substring: `_pick` matched "volume" inside
    # `..._first_quarter_volumeclock`, so the volume role was filled with a
    # *price* (measured 2026-10-10: `mean_high_price_first_quarter_volumeclock`
    # in `volume_gated_momentum`). The signal is self-consistent either way,
    # which is why nothing rejected it — it just is not a volume.
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if volume is None:
        return None
    # Same-field average for the gate, as in `volume_surge` above.
    surge = f"rank({volume} / ts_mean({volume}, {rng.choice([20, 40, 60])}))"
    # The gate is optional: without a PCR field, gate a price signal instead.
    # Options data exists only in USA and IND, so most regions take the fallback.
    pcr = _pick(fields, rng, "pcr", "put_call")
    if pcr is None:
        pcr = _pick(fields, rng, "close")
        if pcr is None:
            return None
        return f"trade_when({surge} > 0.5, ts_delta({pcr}, 20), -1)"
    return f"trade_when({surge} > 0.5, {pcr}, -1)"


def covariance_divergence(fields, rng):
    """Price-volume co-movement: the community's fourth operator, barely ours.

    `ts_covariance` appears in 1,851 mined forum skeletons — fourth behind
    `rank`, `ts_corr` and `subtract` — and this generator has emitted it 38
    times in 49,415 recorded expressions (measured 2026-10-12). The corpus's
    correlation shapes wrap their operands in `rank` (e.g.
    `-1*ts_corr(rank(f1), rank(f2), 10)`), which this follows for a second
    reason: a ranked price and a ranked volume are both unitless, so the
    platform's unit gate at `ts_covariance` cannot reject the pair. The
    unranked form would put a `Unit[CSPrice:1]` against a `Unit[CSShare:1]`.

    Price uses `_pick_price`, not plain `_pick`: its range and derived
    siblings (`..._to_vwap_ratio_*`, `mean_low_ask_size_1min`) are prices only
    in their names, and rank does not make a share count a price. Volume is
    whole-token and refuses the derived `*_volume_ratio_*` family for the
    reason `volume_surge` records — a ratio is already volume-over-average, so
    the covariance would be against a rescaled volume.
    """
    price = _pick_price(fields, rng, "close", "vwap")
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if price is None or volume is None:
        return None
    window = rng.choice([20, 60, 120])
    return f"ts_covariance(rank({price}), rank({volume}), {window})"


def double_gated_momentum(fields, rng):
    """Momentum gated on volume surge *and* cross-sectional strength at once.

    `volume_gated_momentum` above gates on a single condition, and the
    conjunction is the part the pool has never contained: `and` is one of the
    22 operators with zero recorded emissions (measured 2026-10-12), and the
    community corpus uses the multi-condition form — `trade_when` appears in
    1,544 recorded expressions of ours, always with one comparison. Two
    independent conditions ask for a move confirmed by both the tape and the
    cross-section, and they fail differently: a volume spike alone is noise on
    a quiet name, a rank alone is a move nobody traded.

    Both comparisons are unit-safe by construction, which is the constraint
    `volume_gated_momentum` paid for: the volume is compared only against
    `ts_mean` of *itself*, and the momentum leg is a rank, which is unitless
    against the 0.5 constant. The platform gates `greater` on units — 32
    warnings since 10-08 came from comparing two independently drawn fields.
    """
    close = _pick(fields, rng, "close")
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if close is None or volume is None:
        return None
    window = rng.choice([20, 40, 66])
    conditional = f"and({volume} > ts_mean({volume}, {window}), rank(ts_delta({close}, {window})) > 0.5)"
    return f"trade_when({conditional}, ts_delta({close}, {window}), -1)"


def quality_gated_value(fields, rng):
    """A cheapness signal traded only in names that still trade.

    The forum's most directly useful record for this account (post 2026-09-26,
    EUR/TOP2500/d1, ~20 batches). A pure value signal — quarterly EPS over
    price, subindustry-zscored — reached IS Sharpe 1.94-1.96 and still could
    not be submitted: Sub-universe Sharpe pinned at 0.96 against a 1.01 limit,
    the 2Y ladder at 1.56 against 1.58, and prod correlation sitting on the
    line at 0.6986-0.7004. Winsorising, windows, three neutralizations,
    truncation and two-field products did not move it. A **quality gate** did:
    the author kept only names whose retained earnings ranked above the 30th
    percentile of their own year, and *PC fell to 0.5063, sub-universe rose to
    1.07, the 3Y ladder to 2.21, and every check passed*.

    Two details govern this adaptation:

    * the gate is **self-referential and slow** — `ts_rank(ts_backfill(x, 66),
      252) > 0.3` asks whether the name is above its own 30th percentile over
      a year, not how it compares to the cross-section today;
    * the third `trade_when` argument is an **exit condition**. Neither
      `nan` nor -1 requests an exit; when the update condition fails the
      operator retains its previous value. An explicit `if_else` mask is
      needed to make unavailable names flat. The finite operator probes test
      that distinction separately rather than assuming a different book here.

    What cannot transfer is the gate's subject: retained earnings is
    fundamental and out of scope under the pv/option restriction. The proxy
    here is trading activity — "does this name still trade, against its own
    year" — and the signal is the pv analogue of cheapness, price below its
    own 60-day mean. **The PC move is the author's measurement on their factor,
    not ours**; what this registers is the structure, and the check to measure
    it against is the one that blocks our near-misses (0.84-0.92 against 0.7).
    """
    close = _pick(fields, rng, "close")
    volume = _pick_tokens(fields, rng, ("volume",), _RAW_VOLUME_EXCLUDE)
    if close is None or volume is None:
        return None
    window = rng.choice([40, 60, 90])
    return (
        f"trade_when(greater(ts_rank(ts_backfill({volume}, 66), 252), 0.3), "
        f"-({close} / ts_mean({close}, {window}) - 1), nan)"
    )


def iv_skew_reversal(fields, rng):
    """Implied-volatility skew, z-scored over two years and smoothed.

    A straight replication of a shape a community member submitted and
    measured (post 2026-06-10, the Python Alpha Challenge thread):

        rank(ts_decay_linear(ts_zscore(ts_backfill(opt23_iv_call, 22) -
        ts_backfill(opt23_iv_put, 22), 504), 5))
        IS Sharpe 3.73, Fitness 1.55, turnover 0.52, OS ACTIVE, PowerPool.

    Every parameter is theirs — the 22-day backfill, the 504-day z-score, the
    5-day linear decay — because a replicated measurement is the only kind
    this registry can carry: re-drawing the windows would make it a different,
    unmeasured shape wearing the same operator sequence. The pool spells the
    fields differently and holds no option23, so the call/put pair is drawn
    per cell by `_pick_iv_skew_pair`, which pairs by same tenor within one
    dataset.

    Options data exists in USA and IND only, and this template has no
    fallback: elsewhere `_pick_iv_skew_pair` returns None, the generator falls
    back to a built-in, and a registry sweep reports this one as never
    emitting in those cells. That is the shape's boundary rather than a
    starvation defect — the signal *is* the options data — and it is the
    difference from `options_pcr_volume_gated`, which was given a PCR-less
    branch so it would emit everywhere.
    """
    pair = _pick_iv_skew_pair(fields, rng)
    if pair is None:
        return None
    call, put = pair
    return f"rank(ts_decay_linear(ts_zscore(ts_backfill({call}, 22) - ts_backfill({put}, 22), 504), 5))"
