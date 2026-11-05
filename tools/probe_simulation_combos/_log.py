"""Logger for probe_simulation_combos."""

import logging
import sys

from tools.probe_simulation_combos._config import LOG_PATH

log = logging.getLogger("probe_sim")
log.setLevel(logging.DEBUG)

_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_console)

_file = logging.FileHandler(LOG_PATH, mode="a")
_file.setLevel(logging.DEBUG)
_file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_file)

sys.stdout.reconfigure(line_buffering=True)
