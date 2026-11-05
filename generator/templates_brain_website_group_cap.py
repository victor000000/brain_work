"""Group and market-cap templates for the BRAIN website registry.

Split out of `generator/templates_brain_website.py`, which re-exports these
names so `from generator.templates_brain_website import ...` keeps resolving.
"""

from generator.templates_brain_website_pick import _pick, _pick_cap, _pick_group, _pick_price, _pick_return


def capm_residual(fields, rng):
    """CAPM residual - idiosyncratic return after market adjustment."""
    returns = _pick_return(fields, rng)
    cap = _pick_cap(fields, rng)
    sector = _pick_group(rng)
    if returns is None or cap is None:
        return None
    # `rank`, not `log`: `log` takes `Unit[]` and a market cap is
    # `Unit[TSPrice:1,TSShare:1]`, so `log(ts_mean({cap}, 21))` was rejected at
    # index 0 on every fill that reached a real cap field — 245 log-index-0
    # warnings tied to `cap`, and 44% of this template's alphas since 10-08.
    # `_pick_cap` (2026-10-10) is what made it bite: before that the role drew
    # capital-expenditure fields, which are dimensionless and passed.
    return f"ts_regression({returns}, group_mean({returns}, rank(ts_mean({cap}, 21)), {sector}), 252, rettype=0)"


def group_zscore_sector(fields, rng):
    """Manual group z-score within sector.

    The pv/option catalog's `group_zscore_manual` is this same expression.
    """
    field = _pick(fields, rng, "return", "close", "volume")
    sector = _pick_group(rng)
    if field is None:
        return None
    return f"({field} - group_mean({field}, 1, {sector})) / group_std_dev({field}, {sector})"


def cap_decile_neutralized(fields, rng):
    """Neutralize within market cap deciles."""
    signal_field = _pick(fields, rng, "return", "close", "volume")
    cap = _pick_cap(fields, rng)
    if signal_field is None or cap is None:
        return None
    return f"group_neutralize({signal_field}, bucket(rank({cap}), range='0,1,0.1'))"


def capm_beta(fields, rng):
    """CAPM beta - measures systematic risk relative to sector."""
    returns = _pick_return(fields, rng)
    cap = _pick_cap(fields, rng)
    sector = _pick_group(rng)
    if returns is None or cap is None:
        return None
    # See capm_residual on `rank` in place of `log` — same expression, same
    # rejection (39% of this template's alphas since 10-08).
    return f"ts_regression({returns}, group_mean({returns}, rank(ts_mean({cap}, 21)), {sector}), 252, rettype=2)"


def dual_bucket_neutralized(fields, rng):
    """Neutralize within a grid of the signal's own long-term view and volatility.

    The GLB dual-bucket recipe, from the forum post with the fullest ablation
    record in the corpus (2026-09-20: Sharpe 6.24, prod correlation 0.79 →
    0.68, fifteen ablations). Four steps, each with the number that justifies
    it:

    1. **Standardize within industry first** — without it, industry structure
       contaminates every bucket that follows (Sharpe 6.24 → 6.06, the 2Y leg
       5.46 → 5.16).
    2. **Two axes, five bins each**: `bucket(rank(ts_std_dev(x, 22)),
       range='0,1,0.2')` and `bucket(rank(ts_mean(x, 252)), range='0,1,0.2')`.
       The windows are argued rather than tuned — 22 days is the signal's own
       refresh cycle, 252 the shortest meaningful "long-term view" — and 0.2
       granularity measured as a plateau (0.25/0.2/0.1 → 6.22/6.24/6.27), not
       a spike to be fitted.
    3. **`group_cartesian_product`** of the two: the axes must *cross*, not
       nest. Both derive from the same signal and neither contains the other,
       which is what makes the product a valid grouping.
    4. **`group_neutralize` within the cells, not `group_zscore`.** Demeaning
       keeps the signal's amplitude, and the post's ablation says the
       amplitude is load-bearing: z-score instead and Sharpe 5.92, margin
       14.2bp → 10.6bp, fitness 5.26 → 4.31.

    The mechanism, read off the book rather than asserted: the raw signal's
    long leg holds 4,868 names against 4,045 short — the long-term view is net
    long by 800, and that shared exposure is what everyone else is also
    holding. Crossing the axes and neutralizing inside the 25 cells cuts the
    gap to 178, which is the prod-correlation drop.

    `x` is the pv analogue of their model prediction: the daily return, so its
    252-day mean is an opinion held about the name and its 22-day standard
    deviation is how fast that opinion is moving. Their numbers are theirs —
    another account, another dataset — and this registers the structure, to be
    measured against the check it was built to move.
    """
    close = _pick_price(fields, rng, "close")
    if close is None:
        return None
    sector = _pick_group(rng)
    signal = f"{close} / ts_delay({close}, 1) - 1"
    grid = (
        "group_cartesian_product("
        f"bucket(rank(ts_std_dev({signal}, 22)), range='0,1,0.2'), "
        f"bucket(rank(ts_mean({signal}, 252)), range='0,1,0.2'))"
    )
    return f"group_neutralize(group_zscore({signal}, {sector}), {grid})"
