"""Per-template shape-prior weights (P6).

The 1-window vs 2-window hit-rate gap (z=-3.16, p<0.002) found in the F3
follow-up analysis was an empirical signal but the user decision (P6 design,
2026-04-26) was to allow 2-window expressions at full weight and leave F3's
hit_weight to discount them dynamically per cell. The table below encodes
the residual safety rail: ≥3-window templates default to 0.0 (none currently
exist; all base + combo templates are 0, 1, or 2 distinct-window).

Maintenance contract: when a new combo template is added that may produce
≥3 distinct windows in its expanded expression, add an explicit entry
mapping it to 0.0. Failure to add an entry leaves the new template at the
safe default 1.0 — selection treats it as benign. (This is a soft failure;
lint won't catch it.)
"""

# Templates currently in the registry. All produce ≤2 distinct windows.
_SHAPE_WEIGHTS: dict[str, float] = {
    # 0-window (no ts_* operators)
    "power_ratio": 1.0,
    "staleness_decay": 1.0,
    # 1-window
    "raw_regression_long": 1.0,
    "raw_regression_medium": 1.0,
    "scale_rank_zscore": 1.0,
    # 2-window combos (from generator/combo_templates.py)
    "combo_4f_diff": 1.0,
    "combo_4f_product": 1.0,
    "combo_4f_sum": 1.0,
    "combo_5f_delta": 1.0,
    "combo_5f_diff_scale": 1.0,
    # 3-field combos register their full name like "power_ratio+3f_scale" —
    # covered by the default-1.0 fallback below; not enumerated here.
}


def shape_weight(template_name: str) -> float:
    """Return the per-template shape weight.

    Defaults to 1.0 for unknown templates. To gate a template at 0.0, add
    it to _SHAPE_WEIGHTS explicitly.
    """
    return _SHAPE_WEIGHTS.get(template_name, 1.0)
