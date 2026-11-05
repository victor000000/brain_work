"""Tiered scoring: drain near-completion pyramids first, by completion gap.

    gap_to_3 = max(0, 3 - alpha_count)
    tier_weight = {0: 0, 1: 10, 2: 3, 3: 1}[gap_to_3]
    score = tier_weight * multiplier

A 2-alpha pyramid (gap=1, needs +1) outweighs a 1-alpha (gap=2, needs +2)
by ~3x and an uncovered (gap=3, needs +3) by ~10x. Combined with the
yield posterior multiplier from cell_yield_posterior (item 1), a single
near-completion pyramid no longer commandeers the full sim budget.

Within tier, multiplier is the tiebreaker. score=0 (gap=0) means already
complete; the allocator may still explore it for performance improvement.
"""

GAP_TIER_WEIGHT = {0: 0.0, 1: 10.0, 2: 3.0, 3: 1.0}


def compute_targets(alphas_payload, mults_payload, period_start, period_end, refreshed_at):
    """Return list of dicts ready to upsert into pyramid_targets.

    `alphas_payload` is from /pyramid-alphas (alphaCount per pyramid);
    `mults_payload` is from /pyramid-multipliers (multiplier per pyramid).
    """
    mult_map = {
        ((m.get("category") or {}).get("id"), m.get("region"), m.get("delay")): m.get("multiplier", 1.0)
        for m in mults_payload
    }
    rows = []
    for p in alphas_payload:
        cat = (p.get("category") or {}).get("id")
        region = p.get("region")
        delay = p.get("delay")
        if not cat or not region or delay is None:
            continue
        count = p.get("alphaCount", 0) or 0
        mult = mult_map.get((cat, region, delay), 1.0) or 1.0
        gap = max(0, 3 - count)
        score = GAP_TIER_WEIGHT.get(gap, 0.0) * mult
        rows.append(
            {
                "region": region,
                "delay": delay,
                "category": cat,
                "alpha_count": count,
                "multiplier": mult,
                "gap_to_3": gap,
                "score": score,
                "period_start": period_start,
                "period_end": period_end,
                "refreshed_at": refreshed_at,
            }
        )
    return rows
