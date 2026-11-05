"""Build and write the legacy + canonical JSON outputs."""

import json

from tools.discover_simulation_matrix._config import FULL_RESULT_PATH, LEGACY_RESULT_PATH
from tools.discover_simulation_matrix._log import log


def write_outputs(universe_by_region, delay_by_region):
    """Write both the legacy-shape and full canonical JSONs.

    Legacy shape (consumed by tools.apply_discovery_and_redownload):
        {region: {universe: {str(delay): 1}}}
    Full shape: explicit lists + a flat matrix array for downstream tooling.
    """
    legacy = {}
    full_combos = []
    for region in sorted(universe_by_region):
        unis = universe_by_region[region]
        delays = delay_by_region.get(region, [])
        legacy[region] = {}
        for u in unis:
            legacy[region][u] = {str(d): 1 for d in delays}
            for d in delays:
                full_combos.append((region, u, d))

    with open(LEGACY_RESULT_PATH, "w") as f:
        json.dump(legacy, f, indent=2, sort_keys=True)
    log.info("Wrote %s (legacy shape, %d combos)", LEGACY_RESULT_PATH, len(full_combos))

    with open(FULL_RESULT_PATH, "w") as f:
        json.dump(
            {
                "regions": sorted(universe_by_region),
                "universe_by_region": universe_by_region,
                "delay_by_region": delay_by_region,
                "matrix": full_combos,
                "total_combos": len(full_combos),
            },
            f,
            indent=2,
            sort_keys=True,
        )
    log.info("Wrote %s (canonical schema)", FULL_RESULT_PATH)
    return full_combos
