"""Merge and render the `REGION_CONFIGS` matrix that patch_config writes.

Split out of `tools/apply_discovery_and_redownload/patch_config.py`, which
re-exports both names so existing imports keep resolving. Neither function
touches the filesystem — they build the text the patcher validates and writes.
"""

from core.regions import REGION_CONFIGS


def _merged(discovered):
    """Union the canonical matrix with `discovered`, preserving existing order.

    Existing combos keep their position; discovered-only combos are appended,
    regions sorted, universes and delays sorted within a region.
    """
    combos = [(r, u, int(d)) for r, u, d in REGION_CONFIGS]
    seen = set(combos)
    for region in sorted(discovered):
        info = discovered[region]
        for universe in sorted(info["universes"]):
            for delay in sorted(int(d) for d in info["delays"]):
                if (region, universe, delay) not in seen:
                    seen.add((region, universe, delay))
                    combos.append((region, universe, delay))
    return combos


def _render_list(combos):
    """Render the tuples, in order, as the `REGION_CONFIGS = [...]` literal.

    A comment marks each region's block. Order is preserved exactly as merged,
    so the renderer round-trips and the diff shows only real additions.
    """
    counts: dict = {}
    for region, universe, delay in combos:
        counts.setdefault(region, []).append((universe, delay))

    lines = ["REGION_CONFIGS = ["]
    current = None
    for region, universe, delay in combos:
        if region != current:
            pairs = counts[region]
            delays = sorted({d for _u, d in pairs})
            lines.append(
                f"    # {region}: {len({u for u, _d in pairs})} universes, "
                f"{'delay' if len(delays) == 1 else 'delays'} {', '.join(str(d) for d in delays)}"
            )
            current = region
        lines.append(f'    ("{region}", "{universe}", {delay}),')
    lines.append("]")
    return "\n".join(lines) + "\n"
