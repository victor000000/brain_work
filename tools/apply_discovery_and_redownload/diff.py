"""Diff discovered combos against download.fetch_fields.REGION_CONFIG."""

from download.fetch_fields import REGION_CONFIG


def new_combos_vs_region_config(discovered):
    """Return list of (region, universe, delay) tuples in `discovered` that
    aren't already in REGION_CONFIG."""
    out = []
    for region, info in discovered.items():
        old = REGION_CONFIG.get(region, {"universes": [], "delays": []})
        old_unis, old_delays = set(old["universes"]), set(old["delays"])
        for u in info["universes"]:
            for d in info["delays"]:
                if u not in old_unis or d not in old_delays:
                    out.append((region, u, d))
    return out
