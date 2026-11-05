"""Logger for apply_discovery_and_redownload.

Uses a distinct logger name (`apply_disc`) so handlers don't collide with
download.brain_data / download.session, both of which attach to "dl".
"""

import logging
import sys

from tools.apply_discovery_and_redownload._config import LOG_PATH

log = logging.getLogger("apply_disc")
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
