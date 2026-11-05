"""Resolve the combo list from CLI args (--combos / --discovery / default)."""

import json

from tools.probe_simulation_combos._config import DISCOVERY_JSON


def load_combos(args):
    """Return list of (region, universe, delay) tuples per CLI selection."""
    if args.combos:
        out = []
        for spec in args.combos:
            r, u, d = spec.split("/")
            d = int(d.lstrip("d"))
            out.append((r, u, d))
        return out
    if args.discovery:
        with open(DISCOVERY_JSON) as f:
            raw = json.load(f)
        out = []
        for r, unis in raw.items():
            for u, delays in unis.items():
                for d_str in delays:
                    out.append((r, u, int(d_str)))
        return out
    # Default: probe core.regions.REGION_CONFIGS — imported lazily so the
    # tool also works when core.regions can't be imported (e.g., running
    # against a stripped-down install).
    from core.regions import REGION_CONFIGS

    return list(REGION_CONFIGS)
