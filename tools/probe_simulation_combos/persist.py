"""Write probe results to RESULT_PATH."""

import json

from tools.probe_simulation_combos._config import RESULT_PATH
from tools.probe_simulation_combos._log import log


def dump_results(results):
    with open(RESULT_PATH, "w") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    log.info("-" * 60)
    log.info("Wrote %s", RESULT_PATH)
