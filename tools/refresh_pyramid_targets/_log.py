"""Logger setup for refresh_pyramid_targets."""

import logging
import sys

from tools.refresh_pyramid_targets._config import LOG_PATH

log = logging.getLogger("pyramid_targets")
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
