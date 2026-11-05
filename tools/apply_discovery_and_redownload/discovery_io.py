"""Load discover_universes.json into the (region -> universes/delays) shape."""

import json
import os
import sys

from tools.apply_discovery_and_redownload._config import DISCOVERY_JSON
from tools.apply_discovery_and_redownload._log import log


def load_discovery():
    """Read JSON; return dict[region] -> {'universes': set, 'delays': set}."""
    if not os.path.exists(DISCOVERY_JSON):
        log.error("Discovery JSON missing: %s", DISCOVERY_JSON)
        sys.exit(1)
    with open(DISCOVERY_JSON) as f:
        raw = json.load(f)
    out = {}
    for region, universes in raw.items():
        for universe, delays in universes.items():
            for delay_str in delays:
                out.setdefault(region, {"universes": set(), "delays": set()})
                out[region]["universes"].add(universe)
                out[region]["delays"].add(int(delay_str))
    return out
